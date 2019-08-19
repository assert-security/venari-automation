#!/usr/bin/env python3
from pathlib import Path
from typing import List
from configuration import Configuration,ScanTestDefinition
from venariapi.models import JobStatus
from venariapi import VenariAuth,VenariApi
import venariapi.examples.credentials as creds
import yaml
import os
import pathlib
import json
import codecs
import subprocess
import click
from itertools import chain
import json
import re
from urllib.parse import urlparse,ParseResult
import time
import asyncio
import aiohttp
from aiohttp import ClientSession
import logging
logger = logging.getLogger('testdeployment')
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(levelname)s: %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

def get_template(test_def:ScanTestDefinition,template_path)->dict:
    '''
    Takes a ScanTestDefintion and changes the start url in the specified job template to match what is in the test.

    Returns:
        A json patch that can be upload as a job template to the master node.
    '''

    #try to open our template file
    fullPath=os.path.join(template_path,test_def.template_file)
    data=None
    with open(fullPath) as template_file:
        data=template_file.read()
        json_data=json.loads(data)
        return json_data

def get_config(testconfig_path):
    config=None
    with open(testconfig_path, 'r') as yaml_file:
        json_data = yaml_file.read()
        config = Configuration.from_json(yaml.load(json_data,Loader=yaml.SafeLoader))

    return config
    
def import_templates(config: Configuration):
    auth = creds.load_credentials(config.master_node)
    #we are authenticated at this point.
    api = VenariApi(auth,config.master_node)

    for application in config.tests:
        #test:ScanTestDefinition= next (x for x in config.tests if x.name== 'wavesep concurrent')
        if (application):
            template = get_template(application,"./job-templates")
            #Import the job template and remap the template's endpoint/hosts to what's in our test.
            api.import_template(template, application.workspace, application.endpoint)
            #now import the workflows
            if(application.workflows):
                for w in application.workflows:
                    fullPath=os.path.join(".","job-templates",w)
                    with codecs.open(fullPath,"r",encoding="utf-8") as workflow_file:
                        text=workflow_file.read()
                        api.import_workflow(text,application.workspace)

def create_secrets():
    secret_files=['idp-admin-password','jobnode-client-secret','license.lic','server-ssl-cert.pfx','venari-CA.crt']
    secret_files=[os.path.join(Path.home(),'assert-security/secrets',x) for x in secret_files]
    for f in secret_files:
        sname=os.path.basename(f)
        if subprocess.run(f"docker secret inspect {sname}",stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode !=0:
            proc=subprocess.run(f"docker secret create {sname} {f}")
    logger.debug(secret_files)

def shutdown_stack():
    subprocess.run("docker stack rm whitesnake")
    time.sleep(5)

async def fetch_http_status_code(url: str, session: ClientSession, **kwargs) -> int:
    """GET request wrapper to fetch page HTML.

    kwargs are passed to `session.request()`.
    """
    logger.debug(f"fetching: {url}")
    resp = await session.request(method="GET", url=url, **kwargs)
    resp.raise_for_status()
    #html = await resp.text()
    logger.debug(f"Got response {resp.status} for URL: {url}")
    return (url,resp.status)

def build_stack(swarm_hostname:str,config_path:str,tests:List[ScanTestDefinition],service_basename="whitesnake"):
    test_map={x.name : x for x in tests}
    #Take all the stack_files from the tests, plus a few extra, and create docker-compose params to specify each file.
    #Each file will be specified using a full path.
    stack_files=[[x.stack_file for x in tests if(x.stack_file)],['local-network.yml','venari-stack.yml'] ]
    stack_files= [i for i in chain.from_iterable(stack_files)]
    stack_files=["-f "+os.path.join(config_path,x)  for x in stack_files]
    #Run the 'config' command so docker-compose will create a single yml file with all of our services/networks etc.
    stack_files.append('config')
    args=' '.join(stack_files)
    args="docker-compose " + args
    with open("docker-compose.yml",'wb') as cfile:
        proc=subprocess.run(args,stdout=subprocess.PIPE)
        if(proc.returncode == 0):
            cfile.write(proc.stdout)
        else:
            print(proc.stdout)
            exit(1)
        
    logger.debug("Deploying stack")
    #Not sure why this is necessary. For some reason killing the stack and immediately trying to start it complains about not being able to create the network.
    for retry in range(3):
        #now wait for services to come up.
        proc=subprocess.run("docker stack deploy -c docker-compose.yml --with-registry-auth whitesnake ")
        urls:List[str]=[]
        if proc.returncode ==0:
            output:str=subprocess.check_output('docker stack services whitesnake --format "{{json .}}"')
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
                    if(not name in test_map):
                        raise Exception(f"could not find test name that matches docker service name {name}")
                    testUrl:ParseResult=urlparse(test_map[name].endpoint)
                    ping_endpoint=f"{testUrl.scheme}://{swarm_hostname}:{port}{testUrl.path}{testUrl.query}"
                    urls.append({"name":name,"url":ping_endpoint})
                else:
                    logger.warning(f"{name} does not have a published port.")

            loop=asyncio.get_event_loop()
            loop.run_until_complete(wait_for_services(urls))
            break
        else:
            logger.warning("Retrying deploy")
            time.sleep(5)
            
async def wait_for_services(svcs:List[str]):
    tasks = []
    async with ClientSession() as session:    
        for retry in range(10):
            try:
                for svc in svcs:
                    name=svc["name"]
                    url=svc["url"]
                    tasks.append(
                        fetch_http_status_code(url,session)
                    )
                result=await asyncio.gather(*tasks)
                logger.debug(result)
                break
            except Exception as e:
                logger.warning(f"All services did not respond. Retrying: {e}")
                time.sleep(5)
                tasks.clear()
        await session.close()
@click.group()
def cli():
    pass

@cli.command()
@click.option('--testconfig',nargs=1,required=True)
@click.option('--swarmhost',nargs=1,default="host.docker.internal")
def run(testconfig,swarmhost:str):
    shutdown_stack()
    create_secrets()
    config_path=os.path.dirname(testconfig)
    config = get_config(testconfig)
    build_stack(swarmhost,config_path,config.tests)


if __name__ == '__main__':
    cli()
