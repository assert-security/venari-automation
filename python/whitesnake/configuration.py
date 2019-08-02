from enum import IntEnum,Enum
from venariapi.models import JobStatus

from venariapi import VenariAuth,VenariApi
import venariapi.examples.credentials as creds
import json
from pathlib import Path
from typing import List

import yaml

class TestState(Enum):
    pass 


class ScanTestDefinition(object):
    '''
    Defines a scan test. 
    Attributes:
        name (str): The name of the test
        workspace (str): The workspace name the scan job belongs to
        template_name (str): The template to run the scan job with.
    '''
    def __init__(self,name:str,workspace:str=None,template_name:str=None,replace_starturl:str=None,template_file:str=None,workflows:List[str]=None):
        
        self.name=name
        self.template_name=template_name
        self.workspace=workspace
        self.replace_starturl=replace_starturl
        self.template_file=template_file
        self.workflows=workflows


    @classmethod
    def from_json(cls, json_data: dict):
         return cls(**json_data)

class Configuration(object):
    '''
    A Configuration object defines the set of tests that can be run and what
    master node to run them on.
    '''
    def __init__(self,master_node:str,tests:List[ScanTestDefinition]):
        self.master_node=master_node
        self.tests=tests

    @classmethod
    def from_json(cls, json_data: dict):
        tests = list(map(ScanTestDefinition.from_json,json_data["tests"] ))
        json_data["tests"]=tests
        return cls(**json_data)

