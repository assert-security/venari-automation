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
import getpass
from cryptography.fernet import Fernet

class WhitesnakeConfigIdp(object):
    def __init__(
        self,
        external_url:str,
        client_secret:str,
        client_id:str,
        extra:[],
    ):
        self.external_url=external_url
        self.client_secret=client_secret
        self.client_id=client_id
        self.extra=extra
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class WhitesnakeConfig(object):
    def __init__(
        self,
        registry_password:str=None,
        registry_username:str=None,
        docker_password:str=None,
        docker_username:str=None,
        idp=None,
        swarm_master_hostname:str="docker-desktop",
        master_url:str="https://host.docker.internal:9000",
        swarm_manager_hostname:str="host.docker.internal",
        use_tls:bool=False,
        stack_name="whitesnake",
        master_alias="venarimaster"
    ):
        self.registry_password=registry_password
        self.registry_username=registry_username
        self.docker_password=docker_password
        self.docker_username=docker_username
        if(isinstance(idp,dict)):
            self.idp=WhitesnakeConfigIdp.from_dict(idp)
        else:
            self.idp=idp
        self.swarm_master_hostname=swarm_master_hostname
        self.master_url=master_url
        self.swarm_manager_hostname=swarm_manager_hostname
        self.use_tls=use_tls
        self.stack_name=stack_name
        self.master_alias=master_alias

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    @classmethod
    def load(cls,key:str=None):
        settingsFile=os.path.join(Path.home(),'assert-security/whitesnake-auth.json')
        if os.path.exists(settingsFile):
            with open(settingsFile) as settings_file:
                data=settings_file.read()
                json_data=json.loads(data)
                config=WhitesnakeConfig.from_dict(json_data) 
                #decrypt everything
                if config.registry_password != "":
                    config.registry_password=config.decrypt(key,config.registry_password)
                if config.docker_password != "":
                    config.docker_password=config.decrypt(key,config.docker_password)
                return config
        else:
            return None

    def save(self,key:str):
        settingsFile=os.path.join(Path.home(),'assert-security/whitesnake-auth.json')
        self.registry_password=self.encrypt(key,self.registry_password)
        self.docker_password=self.encrypt(key,self.docker_password)
        json_data = json.dumps(self.__dict__, default=lambda o: o.__dict__, indent=4)
        with open(settingsFile,'w') as settings_file:
            settings_file.write(json_data)

        
    def login_interactive(self):
        lastExitCode=1
        while lastExitCode != 0:
            if self.docker_username == "":
                self.docker_username=input("Docker Hub username:")
            
            if self.docker_password == "":
                self.docker_password=getpass.getpass(prompt='Docker Hub password:')    
            lastExitCode=self.login_dockerhub()
            if lastExitCode!=0:
                self.docker_password=""
                self.docker_username=""

        lastExitCode= 1
        while lastExitCode != 0:
            if self.registry_username == "":
                self.registry_username=input("Assert Registry Username:")

            if self.registry_password=="":
                self.registry_password=getpass.getpass(prompt='Assert Registry password:')    
            lastExitCode=self.login_registry()
            if lastExitCode!=0:
                self.registry_password=""
                self.registry_username=""

    
    def login_dockerhub(self)->int:
        cmdLine=["docker","login","--username",self.docker_username,"--password-stdin"]
        proc=subprocess.run(cmdLine,text=True,input=self.docker_password)
        return proc.returncode
    
    def login_registry(self)->int:
        cmdLine=["docker","login","registry.assertsecurity.io","--username",self.registry_username,"--password-stdin"]
        proc=subprocess.run(cmdLine,text=True,input=self.registry_password)
        lastExitCode =proc.returncode
        return lastExitCode

    def login(self):
        self.login_dockerhub()
        self.login_registry()

    def encrypt(self,key:str,text:str)->str:
        cipher_suite = Fernet(key.encode())
        ciphered_text = cipher_suite.encrypt(text.encode())   #required to be bytes
        return ciphered_text.decode()

    def decrypt(self,key:str,ciphered_text:str)->str:
        cipher_suite = Fernet(key.encode())
        unciphered_text = (cipher_suite.decrypt(ciphered_text.encode())).decode()
        return unciphered_text


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

def get_test_config(testconfig_path):
    config=None
    with open(testconfig_path, 'r') as yaml_file:
        json_data = yaml_file.read()
        config = Configuration.from_json(yaml.load(json_data,Loader=yaml.SafeLoader))

    return config
    
def import_templates(config: Configuration,api:VenariApi):
   
    for application in config.tests:
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
                

def create_secrets(docker:Docker,secret_prefix:str,secrets_folder:str=None):
    if(secrets_folder is None):
        secrets_folder=os.path.join(Path.home(),'assert-security/secrets')

    secret_files=['jobnode-client-secret','license.lic','server-ssl-cert.pfx','venari-CA.crt']
    secret_files=[os.path.join(secrets_folder,x) for x in secret_files]
    docker.create_secrets_from_files(secret_files,secret_prefix)
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
@click.option('--importonly/--no_importonly')
@click.option('--farm_only/--no_farm_only')
@click.option('--node_count',default=1,help="Number of job node containers to start.")
@click.option('--secrets_folder',default=None)
@click.option('--verify_ssl/--no_verify_ssl',default=True)
@click.option('--encrypt_key',help="Encryption key for stored settings")
def run(
        testconfig,
        importonly:bool,
        node_count:int,
        secrets_folder:str,
        verify_ssl:bool,
        farm_only:bool,
        encrypt_key:str
    ):
    if encrypt_key is None:
        key=get_or_generateKey(False)
    else:
        key=encrypt_key

    config=WhitesnakeConfig.load(key)
    config.login()
    
    VenariRequestor.verify_ssl=verify_ssl
    config_path=os.path.dirname(testconfig)
    test_config = get_test_config(testconfig)
    master_port=urlparse(config.master_url).port    
    docker_env={
        "IDP_EXTERNAL_URL":config.idp.external_url,
        "MASTER_EXTERNAL_PORT":str(master_port),
        "NODE_COUNT":str(node_count),
        "MASTER_SWARM_NODE_HOSTNAME":config.swarm_master_hostname,
        "MASTER_ALIAS":config.master_alias,
        "SN_PREFIX":config.stack_name
    }
    logger.debug(f"docker_env: {docker_env}")

    if(not importonly):
        docker=get_docker(config.swarm_manager_hostname,config.use_tls)
        docker.shutdown_stack(config.stack_name)
        create_secrets(docker,config.stack_name,secrets_folder)
        
        if(not farm_only):
            build_stack(docker,config.swarm_manager_hostname,config_path,test_config.tests,docker_env)
            asyncio.run(deploy_stack(docker,test_config.tests))
        else:
            build_stack(docker,config.swarm_manager_hostname,config_path,[],docker_env)
            asyncio.run(deploy_stack(docker,[]))
    
    test_config.master_node=config.master_url
    token_endpoint=VenariApi.get_token_endpoint(config.idp.external_url)
    auth=VenariAuth.login(token_endpoint,config.idp.client_secret,config.idp.client_id,config.idp.extra)
    if auth is None:
        raise Exception("Failed to log into idp")
    api=VenariApi(auth,test_config.master_node)

    if(not farm_only):
        import_templates(test_config,api)    

    #print any errors if tests are not valid.
    for t in test_config.tests:
        if(not t.is_valid):
            logger.warning(f"Test {t.name} is INVALID. Reason: {t.invalid_reason}")
        else:
            logger.info(f"Test {t.name} is VALID")

# @cli.command()
# @click.option('--dockerhost',required=False,help="hostname of docker engine. Omit if using local engine.")
# @click.option('--tls/--no_tls',help="Use TLS authentication when talking to the docker engine")
# @click.option('--stack_file',help="Idp stack file to deploy")
# @click.option('--node_hostname',default="docker-desktop",help="hostname of the swarm node to run the idp on.")
# @click.option('--secrets_folder',default=None)
# def idp(dockerhost:bool,tls:bool,stack_file:bool,node_hostname,secrets_folder:str):
#     docker=get_docker(dockerhost,tls)
#     deploy_idp(docker,stack_file,node_hostname,secrets_folder)

def deploy_idp(docker:Docker,stack_file:bool,node_hostname:str,idp_url:str,secrets_folder:str):
    secrets_prefix="identityserver4_"

    docker.delete_secrets(secrets_prefix)
    port=urlparse(idp_url).port    
    env={
        "IDP_EXTERNAL_PORT":f"{port}",
        "SN_PREFIX":secrets_prefix,
        "MASTER_SWARM_NODE_HOSTNAME":node_hostname,
    }
    files=[stack_file]
    create_idp_secrets(docker,secrets_prefix,secrets_folder)
    docker.build_compose_file(env,files)
    #docker.deploy_stack(dockerhost,"authserver",{"authserver":{"name":"authserver","testpath":"/","url":"https://host.docker.internal:9002","status":"404"}})
    docker.deploy_stack("idp")
    # idp uses a well-known location that's passed in, so verify connectivity to that.

# @cli.command()
# @click.option('--client_id',nargs=1,required=True)
# @click.option('--extra_idp',multiple=True,nargs=2)
# @click.option('--secret',nargs=1)
# @click.option('--idp_url',nargs=1,required=True)
# @click.option('--master_url',nargs=1,required=True)
# @click.pass_context
# def saveauth(master_url,idp_url,client_id,extra_idp,secret):
#      try:
#           if(not secret):
#                secret=getpass.getpass(prompt='client secret:')
#           token_endpoint=VenariApi.get_token_endpoint(idp_url.authority)
#           VenariAuth.login(token_endpoint,secret,client_id,extra_idp)
#           creds.save_credentials(master_url,token_endpoint,secret,client_id,extra_idp)
#           print("login successful")
#      except Exception as e:
#           print(f"login failed: {repr(e)}")
#           traceback.print_exc(file=sys.stdout)

def get_docker(dockerhost:str,use_tls:bool)->Docker:
    host=dockerhost
    if dockerhost is not None and use_tls:
        host+=":2376"
    docker=Docker(host,use_tls)
    return docker

def prompt_password(prompt:str,confirm:bool=False)->str:
    done=False
    password=None
    confirm_pass=None
    while not done:
        password=getpass.getpass(prompt=prompt) 
        print(f"pass={password}")
        if confirm:
            confirm_pass=getpass.getpass("Confirm:")
            if password == confirm_pass and password is not None:
                done=True
            else:
                print("Password mismatch.")
                done=False
        else:
            done=True
    if password == "":
        return None
    return password


def get_or_generateKey(generate:bool=False)->str:
    key_file=os.path.join(Path.home(),'assert-security/whitesnake.key')
    key=None
    if os.path.exists(key_file):
        with open(key_file) as file:
            key=file.read()
            logger.debug("found key")
    elif generate:
        key = Fernet.generate_key().decode()
        with open(key_file,"w") as file:
            logger.debug(f"wrote key to {key_file}")
            file.write(key)
    return key



@cli.command()
@click.option('--idp_stack',required=True)
@click.option('--encrypt_key',default=None)
def config(idp_stack,encrypt_key:str):
    
    if encrypt_key is None:
        key=get_or_generateKey(True)
    else:
        key=encrypt_key

    config=WhitesnakeConfig.load(key)
    config.login_interactive()
    config.save(key)
    
    docker=get_docker(config.swarm_manager_hostname,config.use_tls)
    docker.shutdown_stack("idp")
    deploy_idp(docker,idp_stack,config.swarm_master_hostname,config.idp.external_url,secrets_folder=None)
    for retry in range(10):
        try:
            if(retry > 1):
                logger.warning("retrying")
            else:
                logger.info(f"connecting to {config.external.url}")
            token_endpoint=VenariApi.get_token_endpoint(config.idp.external_url)    
            logger.info(f'got token endpoint: {token_endpoint}')
            logger.info("Logging into idp")
            auth=VenariAuth.login(token_endpoint,config.idp.client_secret,config.idp.client_id,config.idp.extra)
            logger.info("success")
            break
        except Exception as e:
            logger.error("failed")
            time.sleep(3)


if __name__ == '__main__':
    try:
        cli()
    except Exception as e:
        #print(f"login failed: {repr(e)}")
        traceback.print_exc(file=sys.stdout)
        exit(1)

