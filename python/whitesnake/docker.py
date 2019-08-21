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
from aiohttp import ClientSession

class Docker(object):
    def __init__(self,remote_host=None,useTls=False):
        self.host_params=f"-H {remote_host}"
        if(useTls):
            self.host_params=f"{self.host_params} --tlsverify"
        print(f"docker ctor: {self.host_params}")
    
    def create_secrets_from_files(self,files:List[str]):
        for f in files:
            sname=os.path.basename(f)
            if subprocess.run(f"docker {self.host_params} secret inspect {sname}",stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode !=0:
                logger.warning(f"{sname} secret was not found. Attempting to create.")
                proc=subprocess.run(f"docker {self.host_params} secret create {sname} {f}")
    
        logger.debug(files)

    def shutdown_stack(self,name:str):
        cmdline=f"docker {self.host_params} stack rm whitesnake"
        print(f"shutting down stack: {cmdline}")
        subprocess.run(cmdline)
        time.sleep(5)

    def deploy_stack(self,filename:str,service_basename:str,test_map:dict,swarm_hostname:str):
        #Killing the stack and immediately trying to start it again fails.
        for retry in range(3):  
            #now wait for services to come up.
            proc=subprocess.run(f"docker {self.host_params} stack deploy -c docker-compose.yml --with-registry-auth whitesnake ")
            urls:List[str]=[]
            if proc.returncode ==0:
                output:str=subprocess.check_output(f"docker {self.host_params} stack services whitesnake --format \"{{{{json .}}}}\"")
                for l in output.splitlines():
                    od:dict=json.loads(l)
                    ports:str=od["Ports"]
                    name:str=od["Name"]
                    logger.debug(f"Name={name},port={ports}")
                    if(ports):
                        port=int(re.search(r'\d+', ports).group())
                        # we have the port and the test name. Next, we need to build the external url from
                        # We need to build a "health" url by substituting the test's hostname with the swarmmanager
                        # hostname and the port assigned by docker.
                        name=name.replace(service_basename+"_","")
                        if(name in test_map):
                        # raise Exception(f"could not find test name that matches docker service name {name}")
                            testUrl:ParseResult=urlparse(test_map[name].endpoint)
                            ping_endpoint=f"{testUrl.scheme}://{swarm_hostname}:{port}{testUrl.path}{testUrl.query}"
                            urls.append({"name":name,"url":ping_endpoint})
                    else:
                        logger.warning(f"{name} does not have a published port.")

                loop=asyncio.get_event_loop()
                loop.run_until_complete(self.wait_for_services(urls))
                break
            else:
                logger.warning("Retrying deploy")
                time.sleep(5)

    async def wait_for_services(self,svcs:List[str]):
        tasks = []
        async with ClientSession() as session:    
            for retry in range(10):
                try:
                    for svc in svcs:
                        name=svc["name"]
                        url=svc["url"]
                        tasks.append(
                            self.fetch_http_status_code(url,session)
                        )
                    result=await asyncio.gather(*tasks)
                    logger.debug(result)
                    break
                except Exception as e:
                    logger.warning(f"All services did not respond. Retrying: {e}")
                    time.sleep(5)
                    tasks.clear()
            await session.close()

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
