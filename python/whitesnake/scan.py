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
    auth = creds.loadCredentials(config.master_node)
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
    print(secret_files)

def build_stack(config_path:str,tests:List[ScanTestDefinition]):
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

@click.group()
def cli():
    pass

@cli.command()
@click.option('--testconfig',nargs=1,required=True)
def run(testconfig):
    create_secrets()
    config_path=os.path.dirname(testconfig)
    config = get_config(testconfig)
    build_stack(config_path,config.tests)
    subprocess.run("docker stack deploy -c docker-compose.yml whitesnake ")

if __name__ == '__main__':
    cli()
