#!/usr/bin/env python3
from pathlib import Path
from typing import List
from configuration import Configuration,ScanTestDefinition
from venariapi.models import JobStatus,VerifyEndpointInfo
from venariapi import VenariAuth,VenariApi,VenariRequestor
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
from docker import Docker,ExternalService
import sys
import traceback

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


logger = logging.getLogger('venariapi')
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

def get_template(template_file: str, template_path)->dict:
    '''
    Takes a ScanTestDefintion and changes the start url in the specified job template to match what is in the test.

    Returns:
        A json patch that can be upload as a job template to the master node.
    '''

    #try to open our template file
    fullPath=os.path.join(template_path, template_file)
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
    logger.debug(f"Attempting to authenticate with {config.master_node}")
    auth = creds.load_credentials(config.master_node)
    if(auth is None):
        raise Exception(f"No stored credentials found for master url \"{config.master_node}\"")
    logger.info("Authentication successful")
    logger.debug(auth)
    #we are authenticated at this point.
    api = VenariApi(auth,config.master_node)
    
    for application in config.tests:
        #test:ScanTestDefinition= next (x for x in config.tests if x.name== 'wavesep concurrent')
        if (application):
            try:
                
                template = get_template(application.template_file, "./job-templates")
                if(application.retest_template_file is not None):
                    retest_template = get_template(application.retest_template_file, "./job-templates")
                
                #Import the job templates and remap the template's endpoint/hosts to what's in our test.
                api.import_template(template, application.workspace, application.endpoint)
                if(retest_template is not None):
                    api.import_template(retest_template, application.workspace, application.endpoint)
                
                #now import the workflows
                if(application.workflows):
                    for w in application.workflows:
                        fullPath=os.path.join(".","job-templates",w)
                        with codecs.open(fullPath,"r",encoding="utf-8") as workflow_file:
                            text=workflow_file.read()
                            api.import_workflow(text,application.workspace)
            except Exception as ex:
                type, value, tb = sys.exc_info()
                application.is_valid=False
                application.invalid_reason=str(ex)
                traceback.print_tb(tb)
                

def create_secrets(docker:Docker,secrets_folder:str=None):
    if(secrets_folder is None):
        secrets_folder=os.path.join(Path.home(),'assert-security/secrets')

    secret_files=['idp-admin-password','jobnode-client-secret','license.lic','server-ssl-cert.pfx','venari-CA.crt']
    secret_files=[os.path.join(secrets_folder,x) for x in secret_files]
    docker.create_secrets_from_files(secret_files)
    logger.debug(secret_files)

def build_stack(docker:Docker,swarm_hostname:str,config_path:str,tests:List[ScanTestDefinition],docker_env:dict,service_basename="whitesnake"):
        #Take all the stack_files from the tests, plus a few extra, and create docker-compose params to specify each file.
        #Each file will be specified using a full path.
        stack_files=[[x.stack_file for x in tests if(x.stack_file)],['venari-stack.yml'] ]
        stack_files= [i for i in chain.from_iterable(stack_files)]
        stack_files=[os.path.join(config_path,x)  for x in stack_files]
        docker.build_compose_file(docker_env,stack_files)

async def deploy_stack(docker:Docker,tests:List[ScanTestDefinition]):
    svc_list=[]
    for t in tests:
        logger.debug(f"stack file: {t.stack_file}")
        if(t.stack_file is not None):
            svc_list.append(ExternalService(t.name,urlparse(t.endpoint).port))
    docker.deploy_stack("whitesnake",svc_list)
    #Now we need to verify all of our endpoints. This is the set of urls that are public and defined in the test
    #and those that were defined as docker services. The svc_list will have mapped external endpoints for anything
    #that is published in the stack files. 

    urls:List[VerifyEndpointInfo]=[]
    svc_map={x.svc_name: x for x in svc_list}
    test_map={x.name: x for x in tests}
    for t in tests:
        if(t.name in svc_map):
            #it's a docker service.
            urlendpoint=urlparse(t.endpoint)
            svc:ExternalService=svc_map[t.name]
            urls.append(
                VerifyEndpointInfo(
                    t.name,
                    f"{urlendpoint.scheme}://{svc.external_host_port}",
                    )
            )
        else:
            #it's a public site, use as-is
            urls.append(VerifyEndpointInfo(
                t.name,
                t.endpoint
            ))
    await VenariApi.verify_endpoints_are_up(urls)
    for u in urls:
        test_map[u.name].is_valid = u.is_up
    logger.debug(test_map.values())
    

def create_idp_secrets(docker:Docker,prefix:str,secrets_folder:str=None):
    #Assumes secrets were created using certmgr docker image.
    if(secrets_folder is None):
        secrets_folder=os.path.join(Path.home(),'assert-security/secrets')

    secret_files=['idp-admin-password','server-ssl-cert.pfx','venari-CA.crt','idp-admin-password','jobnode-client-secret']
    secret_files=[os.path.join(secrets_folder,x) for x in secret_files]
    docker.create_secrets_from_files(secret_files,prefix)
    #docker.build_stack(none,)
    logger.debug(secret_files)

@click.group()
def cli():
    pass

@cli.command()
@click.option('--testconfig',nargs=1,required=True,help="Path to whitesnake configuration file")
@click.option('--swarmhost',nargs=1,default="host.docker.internal",help="swarm host name")
@click.option('--tls/--no_tls',help="Use TLS authentication when talking to the docker engine")
@click.option('--importonly/--no_importonly')
@click.option('--farm_only/--no_farm_only')
@click.option('--master',nargs=1,default="https://host.docker.internal:9000")
@click.option('--idp_url',nargs=1,default="https://host.docker.internal:9002")
@click.option('--node_count',default=1,help="Number of job node containers to start.")
@click.option('--secrets_folder',default=None)
@click.option('--verify_ssl/--no_verify_ssl',default=True)
@click.option('--swarm_master_hostname',default="docker-desktop")
@click.option('--master_alias',default='venarimaster',help="the hostname or fqdn of the master node on the overlay network. FQDN is needed when not using self-signed certs.")
@click.option('--skip_deploy/--deploy')
def run(
        testconfig,
        swarmhost:str,
        tls:bool,
        importonly:bool,
        master:str,
        idp_url:str,
        node_count:int,
        secrets_folder:str,
        verify_ssl:bool,
        swarm_master_hostname:str,
        master_alias:str,
        farm_only:bool,
        skip_deploy: bool,
    ):
    VenariRequestor.verify_ssl=verify_ssl
    config_path=os.path.dirname(testconfig)
    config = get_config(testconfig)
    master_port=urlparse(master).port    
    docker_env={
        "IDP_EXTERNAL_URL":idp_url,
        "MASTER_EXTERNAL_PORT":str(master_port),
        # "NETWORK_EXTERNAL":str(net_external),
        "NODE_COUNT":str(node_count),
        "MASTER_SWARM_NODE_HOSTNAME":swarm_master_hostname,
        "MASTER_ALIAS":master_alias
    }
    logger.debug(f"docker_env: {docker_env}")

    if(not importonly and not skip_deploy):
        swarm_endpoint=swarmhost
        if(tls):
            swarm_endpoint+=":2376"
        docker=Docker(swarm_endpoint,tls)
        docker.shutdown_stack("whitesnake")
        create_secrets(docker,secrets_folder)
        
        if(not farm_only):
            build_stack(docker,swarmhost,config_path,config.tests,docker_env)
            asyncio.run(deploy_stack(docker,config.tests))
        else:
            build_stack(docker,swarmhost,config_path,[],docker_env)
            asyncio.run(deploy_stack(docker,[]))
    
    if(master):
         config.master_node=master
    
    if(not farm_only and not skip_deploy):
        import_templates(config)    

    #print any errors if tests are not valid.
    for t in config.tests:
        if(not t.is_valid):
            logger.warning(f"Test {t.name} is INVALID. Reason: {t.invalid_reason}")
        else:
            logger.info(f"Test {t.name} is VALID")

    # TODO - hook up regression runner here

@cli.command()
@click.option('--dockerhost',required=False,help="hostname of docker engine. Omit if using local engine.")
@click.option('--tls/--no_tls',help="Use TLS authentication when talking to the docker engine")
@click.option('--stack_file',help="Idp stack file to deploy")
@click.option('--node_hostname',default="docker-desktop",help="hostname of the swarm node to run the idp on.")
@click.option('--secrets_folder',default=None)
def idp(dockerhost:bool,tls:bool,stack_file:bool,node_hostname,secrets_folder:str):
    host=dockerhost
    if(tls):
        host+=":2376"
    docker=Docker(host,tls)
    secrets_prefix="identityserver4_"
    env={
        "IDP_EXTERNAL_PORT":"9002",
        "SN_PREFIX":secrets_prefix,
        "MASTER_SWARM_NODE_HOSTNAME":node_hostname,
    }
    files=[stack_file]
    create_idp_secrets(docker,secrets_prefix,secrets_folder)
    docker.build_compose_file(env,files)
    #docker.deploy_stack(dockerhost,"authserver",{"authserver":{"name":"authserver","testpath":"/","url":"https://host.docker.internal:9002","status":"404"}})
    docker.deploy_stack("idp")
    # idp uses a well-known location that's passed in, so verify connectivity to that.


if __name__ == '__main__':
    cli()

