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
from docker import Docker

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
    if(auth is None):
        raise Exception(f"No stored credentials found for master url \"{config.master_node}\"")
    logger.debug(auth)
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

def create_secrets(docker:Docker):
    secret_files=['idp-admin-password','jobnode-client-secret','license.lic','server-ssl-cert.pfx','venari-CA.crt']
    secret_files=[os.path.join(Path.home(),'assert-security/secrets',x) for x in secret_files]
    docker.create_secrets_from_files(secret_files)
    logger.debug(secret_files)


def build_stack(docker:Docker,swarm_hostname:str,config_path:str,tests:List[ScanTestDefinition],service_basename="whitesnake"):
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
        newenv=os.environ
        newenv["IDP_EXTERNAL_URL"]="https://master.assertsecurity.io:9002"
        newenv["MASTER_EXTERNAL_PORT"]="9013"
        proc=subprocess.run(args,stdout=subprocess.PIPE,env=newenv)
        if(proc.returncode == 0):
            cfile.write(proc.stdout)
        else:
            print(proc.stdout)
            exit(1)
        
    logger.debug("Deploying stack")
    docker.deploy_stack("docker-compose.yml",service_basename,test_map,swarm_hostname)
               
@click.group()
def cli():
    pass

@cli.command()
@click.option('--testconfig',nargs=1,required=True)
@click.option('--swarmhost',nargs=1,default="orion.corp.assertsecurity.io")
@click.option('--tls/--no_tls')
@click.option('--importonly/--no_importonly')
@click.option('--master',nargs=1)
def run(testconfig,swarmhost:str,tls:bool,importonly:bool,master:str):
    config_path=os.path.dirname(testconfig)
    config = get_config(testconfig)

    if(not importonly):
        swarm_endpoint=swarmhost
        if(tls):
            swarm_endpoint+=":2376"
        docker=Docker(swarm_endpoint,tls)
        docker.shutdown_stack("whitesnake")
        create_secrets(docker)
        build_stack(docker,swarmhost,config_path,config.tests)
    if(master):
        config.master_node=master
    import_templates(config)    

if __name__ == '__main__':
    cli()
