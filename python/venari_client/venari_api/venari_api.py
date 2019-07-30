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

from venari_api.venari_requestor import VenariRequestor
from venari_api.venari_auth import VenariAuth,IdpInfo,RequestHelper
import argparse
from enum import IntEnum
from venari_api.venari_query import VenariQuery
from venari_api.venari_query import JobQuery
from venari_api.venari_query import FindingQuery
import venari_api.models as models

class VenariApi(object):
    def __init__(self, auth, api_url, verify_ssl=True, timeout=60, user_agent=None,
                 token=None, client_version='1.0'):
        self.api_url = api_url
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.client_version = client_version
        self.auth=auth

        if not user_agent:
            self.user_agent = 'venari_api/' + client_version
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

    
    def _request(self, method:str, endpoint:str,json:dict=None,params:dict=None):
        requestor=VenariRequestor(self.auth,self.api_url+endpoint,method,verify_ssl=self.verify_ssl)
        return requestor.request(json,params)
