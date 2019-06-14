#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Brandon Spruth (bspruth@gmail.com)"
__copyright__ = "(C) 2019 Sprtuh, Co."
__contributors__ = ["Brandon Spruth"]
__status__ = "Planning"
__license__ = "MIT"
__since__ = "0.0.1"

import urllib3
import json
import requests
import types
from venari_requestor import *
from venari_auth import *
from venariapi import __version__ as version
import argparse
from query import *
from enum import IntEnum
'''
class SummaryData(object):
    def __init__(self,Name,RuleUniqueID:str,Severity,State,RuleType,Behaviors,DefaultSort,Properties):
        #self.Behaviors=BehaviorSettingsData
        self.Name=Name

    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)

class BehaviorSettingsData(object):
    def __init__(self,DisplayText,UniqueName,Enabled):
        self.DisplayText:DisplayText
        self.UniqueName:UniqueName
        self.Enabled:Enabled
    
    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)

class Finding(object):

    def __init__(self, DetailID: str,ID: str,UniqueID:str,Version:str,SummaryData):
        self.DetailID=DetailID
        self.ID=ID
        self.UniqueID=UniqueID
        self.Version=Version
        self.SummaryData=SummaryData
    @classmethod
    def from_json(cls, json_data: dict):
        json_data["SummaryData"]=SummaryData.from_json(json_data["SummaryData"])
        f= cls(**json_data)
        return f

'''    
  
class DBTypeEnum(IntEnum):
    Global=0
    Job=1
    Workspace=2

class DBData(object):
    def __init__ (self,id,type:DBTypeEnum):
        self.DBID=id
        self.DBType=type

    @staticmethod 
    def from_dict(json:dict):
        data=DBData(json["DBID"],json["DBType"])
        return data


class VenariApi(object):
    def __init__(self, auth, api_url, verify_ssl=True, timeout=60, user_agent=None,
                 token=None, client_version='1.0'):
        self.api_url = api_url
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.client_version = client_version
        self.auth=auth

        if not user_agent:
            self.user_agent = 'venari_api/' + version
        else:
            self.user_agent = user_agent

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Set auth_type based on what's been provided
    
    def get_workspace_by_name(self,workspaceName)->VenariResponse:
        endpoint='/api/workspace'
        data=dict({
            "Name":workspaceName
        })
        return self._request('POST',endpoint,json=data)

    def get_workspaces(self):
        endpoint='/api/workspace/summaries'
        return self._request('GET',endpoint)


    def get_jobs_for_workspace(self,Id)->VenariQueryResult:
        json_data = dict({
            "WorkspaceID": Id,
        })

        endpoint = '/api/jobs'
        r=VenariRequestor(self.auth,self.api+endpoint,'POST',verify_ssl=self.verify_ssl)
        return VenariQueryResult(r,json_data)

    def get_jobs(self)->VenariQueryResult:
        json_data=dict({
            "SortDescending": True,
        })

        endpoint=self.api_url+'/api/jobs'
        r=VenariRequestor(self.auth,endpoint,'POST',verify_ssl=self.verify_ssl)
        return VenariQueryResult(r,json_data)

    def get_findings_for_workspace(self,dbdata:DBData)->VenariQueryResult:
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
        return VenariQueryResult(r,json_data)

    def get_findings_for_job(self,jobUniqueID)->VenariQueryResult:
        """
        Return all finding detail for a job.
        :param: jobid - A job's Unique Id
        :return: A VenariQueryResult that holds:
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
                    "DBType": DBTypeEnum.Job
                },
            }
        )
        endpoint = self.api_url+'/api/findings/get'
        r=VenariRequestor(self.auth,endpoint,'POST',verify_ssl=self.verify_ssl)
        return VenariQueryResult(r,json_data)

    def get_templates_for_workspace(self,db:DBData):
        json_data=dict({
            "DBID":db.DBID,
            "DBType":db.DBType
        })
        endpoint = '/api/job/templates'
        return self._request('POST',endpoint,json=json_data)

    def start_job_fromtemplate(self,job_name,workspace_name,template_name)->VenariResponse:
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
        return self._request('PUT',endpoint=endpoint,json=json_data)
    
    def get_job_summary(self,jobId:int)->VenariResponse:
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
        return self._request("GET",'/api/job/summary',params=params)
    
    def _request(self, method:str, endpoint:str,json:dict=None,params:dict=None):
        requestor=VenariRequestor(self.auth,self.api_url+endpoint,method,verify_ssl=self.verify_ssl)
        return requestor.request(json,params)
