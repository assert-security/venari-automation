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
import dpath

def fixup_jobtemplate(test_def:ScanTestDefinition,template_path)->str:
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
        start_url:None
        for(path,value) in dpath.util.search(json_data,"/Patch",yielded=True):
            for p in value:
                if(p["path"]=="/ResourceScope/SeedResources/StartUrls"):
                    start_url=(p["value"][0])
        start_url=start_url.rstrip('/')
        print(f"start url: {start_url}")
        newdata=data.replace(start_url,test_def.replace_starturl)
        new_json=json.loads(newdata)
        print(json.dumps(new_json,indent=4))


    print(fullPath)
    pass

if __name__ == '__main__':

    config=None
    with open(str(Path.home())+"/.whitesnake.yaml", 'r') as yaml_file:
        json_data = yaml_file.read()
        config=Configuration.from_json(yaml.load(json_data))

    fixup_jobtemplate(config.tests[2],"./job-templates")    

    #auth=creds.loadCredentials(config.master_node)
    #we are authenticated at this point.
    #look for the templates and import them

    
    # api=VenariApi(auth,config.master_node)
    
    # q=api.get_jobs()
    # q.execute()
    # for j in q.items():
    #     print(j)

    #api.start_job_fromtemplate()

