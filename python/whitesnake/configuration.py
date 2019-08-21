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
        endpoint (str): The base url, formatted as <scheme>://<host>[:port], of the server to scan.
    '''
    def __init__(self,
                 name:str,
                 max_missing_findings:int,
                 expected_findings_file:str=None,
                 workspace:str=None,
                 template_name:str=None,
                 endpoint:str=None,
                 template_file:str=None,
                 retest_template_file:str=None,
                 test_url:str=None,
                 test_url_content_pattern:str=None,
                 workflows:List[str]=None,
                 stack_file:str=None):
        
        self.name=name
        self.max_missing_findings = max_missing_findings
        self.workspace=workspace
        self.endpoint=endpoint
        self.template_file=template_file
        self.retest_template_file = retest_template_file
        self.template_name=template_name
        self.test_url = test_url
        self.test_url_content_pattern = test_url_content_pattern
        self.workflows=workflows
        self.expected_findings_file = expected_findings_file
        self.stack_file=stack_file
        self.is_invalid=False
        self.invalid_reason=None

    @classmethod
    def from_json(cls, json_data: dict):
         return cls(**json_data)

class Configuration(object):
    '''
    A Configuration object defines the set of tests that can be run and what
    master node to run them on.
    '''
    def __init__(self,
                 master_node:str,
                 tests:List[ScanTestDefinition],
                 unavailable_app_limit:int = -1,
                 scan_start_fail_limit:int = 0,
                 scan_result_fail_limit:int = 0
        ):
        self.unavailable_app_limit = unavailable_app_limit
        self.scan_start_fail_limit = scan_start_fail_limit
        self.scan_result_fail_limit = scan_result_fail_limit
        self.master_node = master_node
        self.tests = tests

    @classmethod
    def from_json(cls, json_data: dict):
        tests = list(map(ScanTestDefinition.from_json,json_data["tests"] ))
        json_data["tests"]=tests

        return cls(**json_data)

