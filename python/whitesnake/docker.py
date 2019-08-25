import subprocess
from typing import List
import os
import logging
import time
import json
logger = logging.getLogger('testdeployment')
import re
from urllib.parse import urlparse,ParseResult
import asyncio
import subprocess
from aiohttp import ClientSession,ClientConnectorError
from itertools import chain
from configuration import ScanTestDefinition


class ExternalService(object):
    def __init__(self,svc_name:str,internal_port:int,url_path="/"):
        """init method
        
        Arguments:
            svc_name {str} -- Name of docker service as it would appear in a compose file.
            internal_port {int} -- The port the http(s) endpoint listens on inside the container (i.e. 80,808,443, etc.)
        """
        self.svc_name=svc_name
        self.internal_port=internal_port
        #self.url_path=url_path
        self.external_host_port:str=None #Holds the mapped external port of the service.

    def __repr__(self):
        return f"{{svc_name:{self.svc_name},internal_port:{self.internal_port},external_host:{self.external_host_port}}}"

class Docker(object):
    def __init__(self,remote_host=None,useTls=False):
        self.host_params=""
        if(remote_host != "host.docker.internal") and not remote_host is None:
            self.host_params=f"-H {remote_host}"

        if(useTls):
            self.host_params=f"{self.host_params} --tlsverify"
        if(remote_host is not None):
            self.remote_host=remote_host.split(':')[0]
        logger.debug(f"Docker __init__: {self.host_params}")
    
    def create_secrets_from_files(self,files:List[str],prefix:str=None):
        for f in files:
            sname=os.path.basename(f)
            if(prefix):
                sname=prefix+sname
            if subprocess.run(f"docker {self.host_params} secret inspect {sname}",stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode !=0:
                logger.warning(f"{sname} secret was not found. Attempting to create.")
                proc=subprocess.run(f"docker {self.host_params} secret create {sname} {f}")
    
        logger.debug(files)

    def shutdown_stack(self,name:str):
        cmdline=f"docker {self.host_params} stack rm whitesnake"
        print(f"shutting down stack: {cmdline}")
        subprocess.run(cmdline)
        time.sleep(5)

    def deploy_stack(self,service_name:str,svc_list:List[ExternalService]=None,filename:str="docker-compose.yml"):
        """deploy a docker stack file
        
        Arguments:
            filename {str} -- [description]
            service_name {str} -- The docker stack service name to use
            test_map {dict} -- [description]
            swarm_hostname {str} -- [description]
        
        Raises:
            Exception: [description]
        """
        logger.debug(f"deploying {filename}")
        if(svc_list is not None):
            svc_map:dict={x.svc_name : x for x in svc_list}
        else:
            svc_map={}
        #Make sure all the images are present.
        for retry in range(3):  
            #now wait for services to come up.
            cmdline=f"docker {self.host_params} stack deploy -c {filename} --with-registry-auth {service_name} "
            logger.debug(f"running: {cmdline}")
            proc=subprocess.run(cmdline)
            urls:List[str]=[]
            if proc.returncode ==0:
                cmdline=f"docker {self.host_params} stack services {service_name} --format \"{{{{json .}}}}\""
                logger.debug(f"running: {cmdline}")
                output:str=subprocess.check_output(cmdline)
                for l in output.splitlines():
                    od:dict=json.loads(l)
                    ports:str=od["Ports"]
                    name:str=od["Name"]
                    logger.debug(f"Name={name},port={ports}")
                    name=name.replace(service_name+"_","")
                    if(ports):
                        port=int(re.search(r'\d+', ports).group())
                        # update the external host and port to match docker endpoint + mapped port.
                        if(name in svc_map):
                            svc_map[name].external_host_port=f"{self.remote_host}:{port}"
                    else:
                        logger.warning(f"{name} does not have a published port.")

                logger.debug(svc_map)
                break
            else:
                logger.warning("Retrying deploy")
                time.sleep(5)

    def build_compose_file(self,docker_env:dict,input_files:List[str],outfile:str="docker-compose.yml"):
        #Run the 'config' command so docker-compose will create a single yml file with all of our services/networks etc.
        stack_files=["-f "+x for x in input_files]        
        args=' '.join(stack_files)
        args="docker-compose "+args+" config"
        with open(outfile,'wb') as cfile:
            newenv=os.environ
            newenv.update(docker_env)
            logger.debug(f"running: {args}")
            proc=subprocess.run(args,stdout=subprocess.PIPE,env=newenv)
            if(proc.returncode == 0):
                cfile.write(proc.stdout)
            else:
                print(proc.stdout)
                exit(1)
            
        logger.debug("Deploying stack")

    async def fetch_http_status_code(self,url: str, session: ClientSession, **kwargs) -> int:
        """GET request wrapper to fetch page HTML.

        kwargs are passed to `session.request()`.
        """
        logger.debug(f"fetching: {url}")
        resp = await session.request(method="GET", url=url, **kwargs)
        resp.raise_for_status()
        #html = await resp.text()
        logger.debug(f"Got response {resp.status} for URL: {url}")
        return (url,resp.status)
