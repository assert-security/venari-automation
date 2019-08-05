#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Chris Szabo (chris.szabo@assertsecurity.io)"
__copyright__ = "(C) 2019 Assert Security"
__contributors__ = ["Chris Szabo"]
__status__ = "Planning"
__license__ = "MIT"
__since__ = "0.0.1"

import urllib3
import json
import requests
import types
import dpath
import yaml
from urllib.parse import urlparse

from venariapi.venari_requestor import VenariRequestor
from venariapi.venari_auth import VenariAuth,IdpInfo,RequestHelper
import argparse
from enum import IntEnum
from venariapi.venari_query import VenariQuery
from venariapi.venari_query import JobQuery
from venariapi.venari_query import FindingQuery
import venariapi.models as models

class VenariApi(object):
    def __init__(self, auth, api_url, verify_ssl=True, timeout=60, user_agent=None,
                 token=None, client_version='1.0'):
        self.api_url = api_url
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.client_version = client_version
        self.auth=auth

        if not user_agent:
            self.user_agent = 'venariapi/' + client_version
        else:
            self.user_agent = user_agent

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @staticmethod
    def get_idp_info(api_url:str)->IdpInfo:
        url:str=api_url+'/api/auth/idpInfo'
        response=RequestHelper.request('GET',url)
        return IdpInfo(response.data)

    @staticmethod
    def get_token_endpoint(authorityUrl:str):
        """
        Retrieve the token endpoint from the oidc document.
        """
        if(not authorityUrl.endswith("/")):
            authorityUrl=authorityUrl+"/"
        url:str=authorityUrl+".well-known/openid-configuration"
        response=RequestHelper.request('GET',url)
        return response.data["token_endpoint"]
    
    def get_workspace_by_name(self,workspaceName)->models.Workspace:
        endpoint='/api/workspace'
        data=dict({
            "Name":workspaceName
        })
        result=self._request('POST',endpoint,json=data)
        if(result.hasData()):
           return models.Workspace.from_data(result.data)

    def get_workspaces(self):
        endpoint='/api/workspace/summaries'
        result=self._request('GET',endpoint)
        if(result.hasData()):
            return [models.Workspace.from_data(i) for i in result.data]

    def get_jobs_for_workspace(self,Id)->JobQuery:
        json_data = dict({
            "WorkspaceID": Id,
        })

        endpoint = '/api/jobs'
        r=VenariRequestor(self.auth,self.api_url+endpoint,'POST',verify_ssl=self.verify_ssl)
        return JobQuery(r,json_data)

    def get_jobs(self)->JobQuery:
        json_data=dict({
            "SortDescending": True,
        })

        endpoint=self.api_url+'/api/jobs'
        r=VenariRequestor(self.auth,endpoint,'POST',verify_ssl=self.verify_ssl)
        return JobQuery(r,json_data)

    def get_findings_for_workspace(self,dbdata:models.DBData)->VenariQuery:
        """
        Return all workspace/app/scan historical finding detail summary.
        :param:
        :return: Job ID, Scan Name, and Vulnerability Name
        """
        json_data = dict(
            {
                "DBData": {
                    "DBID": dbdata.DBID,
                    "DBType": dbdata.DBType
                },
            }
        )
        endpoint = self.api_url+'/api/findings/get'
        r=VenariRequestor(self.auth,endpoint,'POST',verify_ssl=self.verify_ssl)
        return FindingQuery(r,json_data)

    def get_findings_for_job(self,jobUniqueID)->VenariQuery:
        """
        Return all finding detail for a job.
        :param: jobid - A job's Unique Id
        :return: A VenariQuery that holds:
        "SummaryData": {
            "RuleUniqueID": "string",
            "RuleType": 0,
            "State": 0,
            "Behaviors": [
            {
                "Enabled": true,
                "UniqueName": "string",
                "DisplayText": "string"
            }
            ],
            "Name": "string",
            "Severity": 0,
            "DefaultSort": "string",
            "Properties": {}
        },
        "DetailID": 0,
        "ID": 0,
        "Version": 0,
        "UniqueID": "string"
        """
        json_data = dict(
            {
                "DBData": {
                    "DBID": jobUniqueID,
                    "DBType": models.DBTypeEnum.Job
                },
            }
        )
        endpoint = self.api_url+'/api/findings/get'
        r=VenariRequestor(self.auth,endpoint,'POST',verify_ssl=self.verify_ssl)
        return FindingQuery(r,json_data)

    def get_templates_for_workspace(self,db:models.DBData):
        json_data=dict({
            "DBID":db.id,
            "DBType":db.type
        })
        endpoint = '/api/job/templates'
        resp=self._request('POST',endpoint,json=json_data)

        templates=[]
        if(resp.hasData()):
            templates=[models.JobTemplate.from_data(x) for x in resp.data ]
            return templates

    def start_job_fromtemplate(self,job_name,workspace_name,template_name)->models.JobStartResponse:
        """
        Start a job
        :param job_name: The name of the job template to run
        :param template_name: The name of the template run for the new job
        :param workspace_name: The workspace to store the job in
        :return: Returns a VenariReponse with following data: 
            {
            "Job": {
                "Name": "string",
                "SettingsTypeDisplayName": "string",
                "SettingsID": 0,
                "SharedBaseAddress": "string",
                "Status": 0,
                "CompletedBecause": 0,
                "SharedJob": true,
                "WorkspaceID": 0,
                "DataType": "string",
                "AssignedTo": "string",
                "CreatedDate": "2019-06-14T02:45:33.279Z",
                "Activity": [
                {
                    "StartTime": "2019-06-14T02:45:33.279Z",
                    "EndTime": "2019-06-14T02:45:33.279Z"
                }
                ],
                "DurationTicks": 0,
                "Priority": 0,
                "StatusMessage": "string",
                "ID": 0,
                "Version": 0,
                "UniqueID": "string"
            },
            "Succeeded": true,
            "Message": "string"
            }        """
        json_data=dict({
            "Name": job_name,
            "WorkspaceName": workspace_name,
            "JobTemplateName": template_name
            })
        endpoint ='/api/job/startfromworkspace'
        resp= self._request('PUT',endpoint=endpoint,json=json_data)
        if(resp.hasData()):
            return models.JobStartResponse.from_data(resp.data)
    
    def get_job_summary(self,jobId:int)->models.JobSummary:
        """
        Get summary information about a job.
        :param jobId: Job integer identifier
        :return: Returns a VenariReponse containing:
        {
        "Status": 0,
        "Activity": [
            {
            "StartTime": "2019-06-14T03:49:41.941Z",
            "EndTime": "2019-06-14T03:49:41.941Z"
            }
        ],
        "Statistics": {
            "QueueStatistics": [
            {
                "QueueID": "string",
                "CategoryName": "string",
                "CategorySort": 0,
                "DisplayName": "string",
                "JobUniqueID": "string",
                "ReadyCount": 0,
                "AcquiredCount": 0,
                "RunningCount": 0,
                "CompletedCount": 0,
                "SkippedCount": 0,
                "CancelledCount": 0,
                "ID": 0,
                "Version": 0,
                "UniqueID": "string"
            }
            ],
            "Counters": [
            {
                "Counter": {
                "Name": {
                    "NamePath": [
                    "string"
                    ],
                    "DisplayName": "string"
                },
                "Count": 0,
                "ID": 0,
                "Version": 0,
                "UniqueID": "string"
                },
                "Children": [
                null
                ]
            }
            ],
            "ID": 0,
            "Version": 0,
            "UniqueID": "string"
        },
        "AssignedTo": "string"
        }
        """
        params=dict({
            "jobID":jobId
        })
        resp=self._request("GET",'/api/job/summary',params=params)
        if(resp.hasData()):
            j=models.JobSummary.from_results(resp.data)
            return j

    def import_workflow(self,workflow_text:str,workspace:str)->bool:
        #make sure the workflow is valid parsable yaml.
        yaml.parse(workflow_text,yaml.SafeLoader)
        #Need to get workspace name.
        wobj=self.get_workspace_by_name(workspace)
        params:dict={
            "WorkflowText":workflow_text,
            "DBData":{
                "DBID":wobj.db_data.id,
                "DBType":wobj.db_data.type
            }
        }
        resp=self._request("POST",'/api/workflow/save',json=params)
        print(resp.success)
        return resp.success
    def import_template(self,patch:dict,workspace:str,start_url:str=None):
        '''
        Takes a ScanTestDefintion and changes the start url in the specified job template to match what is in the test.
        Only the scheme, host, and port numbers are used in the start_url. If anything else is specified, an exception
        is thrown. 

        Argsuments:
            
        Returns:
            A json patch that can be upload as a job template to the master node.
        '''
        modified_patch=self._fixup_jobtemplate(patch,start_url)
        '''
        {
        "WorkspaceName": "string",
        "JobTemplateName": "string",
        "SettingsType": "string",
        "SettingsTypeDisplayName": "string",
        "Patch": {}
        }
        '''        
        params=dict({
            "WorkspaceName":workspace,
            "JobTemplateName":modified_patch["JobTemplateName"],
            "SettingsType":modified_patch["SettingsType"],
            "SettingsTypeDisplayName":modified_patch["SettingsTypeDisplayName"],
            "Patch":modified_patch["Patch"]
        })
        resp=self._request("POST",'/api/job/template/import',json=params)
    
    def get_scan_compare_data(self, baseline_json:str, comparison_job_uid:str) -> models.ScanCompareResultData:
        data = dict({
            "BaselineJSON": baseline_json,
            "ComparisonJobID": comparison_job_uid
        })
        response = self._request("POST",'/api/qa/get/comparison/baseline', json = data)
        if (response.hasData()):
            return models.ScanCompareResultData.from_dict(response.data)

    def set_job_status(self, job_id:int, status:models.JobStatus):
        data = dict({
            "ID": job_id,
            "Status": int(status),
        })
        resp = self._request('POST', endpoint = '/api/analysis/job/status', json = data)
        return resp.hasData()

    def delete_workspace(self, workspace_id: int) -> models.OperationResultData:
        data = dict({
            "ID": workspace_id,
            "DeleteAttachedAssets": True,
        })
        resp = self._request('DELETE', endpoint = '/api/workspace', json = data)
        if (resp.hasData):
            return models.OperationResultData.from_dict(resp.data)
        else:
            return models.OperationResultData(False, resp.message)

    
    def _request(self, method:str, endpoint:str,json:dict=None,params:dict=None):
        requestor=VenariRequestor(self.auth,self.api_url+endpoint,method,verify_ssl=self.verify_ssl)
        return requestor.request(json,params)

    def _fixup_jobtemplate(self,template_patch:dict,new_baseurl)->dict:
        endpoint=urlparse(new_baseurl)
        new_baseurl=f"{endpoint.scheme}://{endpoint.netloc}"
        
        print(new_baseurl)

        for(path,value) in dpath.util.search(template_patch,"/Patch",yielded=True):
            for p in value:
                if(p["path"]=="/ResourceScope/SeedResources/StartUrls"):
                    existing_baseurl=(p["value"][0])
                    print(f"original url: {existing_baseurl}")
                    endpoint=urlparse(existing_baseurl)
                    existing_baseurl=f"{endpoint.scheme}://{endpoint.netloc}"

        patch=json.dumps(template_patch)
        newdata=patch.replace(existing_baseurl,new_baseurl)
        new_json=json.loads(newdata)
        return new_json

