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
    

if __name__ == '__main__':

    config=None
    with open(str(Path.home())+"/.whitesnake.yaml", 'r') as yaml_file:
        json_data = yaml_file.read()
        config=Configuration.from_json(yaml.load(json_data))

    for test in config.tests:
        #test:ScanTestDefinition= next (x for x in config.tests if x.name== 'wavesep concurrent')
        if(test):
            template=get_template(test,"./job-templates")
            auth=creds.loadCredentials(config.master_node)
            #we are authenticated at this point.
            api=VenariApi(auth,config.master_node)
            #Import the job template and remap the template's endpoint/hosts to what's in our test.
            api.import_template(template,test.workspace,test.endpoint)

