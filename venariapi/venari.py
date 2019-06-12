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
from request_helper import *
from venari_auth import *
from venariapi import __version__ as version
import argparse

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
class DBData(object):
    def __init__ (self,id,type):
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
    
    def get_workspace_by_name(self,workspaceName):
        endpoint='/api/workspace'
        data=dict({
            "Name":workspaceName
        })
        return self._request('POST',endpoint,json=data)

    def get_workspaces(self):
        endpoint='/api/workspace/summaries'
        return self._request('GET',endpoint)

    def get_workspace_by_name(self,name):
        endpoint='/api/workspace'
        data=dict({
            "Name":name
        })
        return self._request('POST',endpoint,json=data)

    def get_jobs_for_workspace(self,Id):
        """
        List scans
        :param
        :return scan jobs
        """
        json_data = dict(
            {
                "WorkspaceID": 1,
                "Skip": 0,
                "Take": 999,
            }
        )
        endpoint = '/api/jobs'
        return self._request('POST', endpoint, json=json_data)
    def get_jobs(self):
        json_data=dict({
            "SortDescending": True,
            "Skip": 0,
            "Take": 9999,
        })

        endpoint='/api/jobs'
        return self._request('POST', endpoint, json=json_data)

    def get_findings_for_workspace(self,dbdata:DBData):
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
                "SortDescending": True,
                "Skip": 0,
                "Take": 999,
            }
        )
        endpoint = '/api/findings/get'
        return self._request('POST', endpoint, json=json_data)

    def get_detail_scan_findings(self,db:DBData):
        """
        Used to query individual workspace/app/scan finding details.  Need to filter on Severity, Name, Location (URL).
        :param NOT SURE
        :return Workspace, severity, name and location
        """
        json_data = dict(
            {
                "WorkspaceID": 1,
                "Skip": 0,
                "Take": 999,
            }
        )
        endpoint = '/api/findings/detail'
        return self._request('POST', endpoint, json=json_data)

    def get_templates_for_workspace(self,db:DBData):
        json_data=dict({
            "DBID":db.DBID,
            "DBType":db.DBType
        })
        endpoint = '/api/job/templates'
        return self._request('POST',endpoint,json=json_data)


    def start_scan(self):
        """
        :param:
        :return:
        """
        json_data = dict(

        )
        endpoint = ''
        return self._request('POST', endpoint, json=json_data)

    def _request(self, method, endpoint, params=None, files=None, json=None, data=None, headers=None, stream=False):
        """
        Common handler for all HTTP requests, params are for GET and data for POST
        :param params, files, json, data, headers, stream, method, endpoint
        :return response from HTTP request
        """
        if not params:
            params = {}
        if not headers:
            headers = {'Accept': 'application/json'}
        # not sure where this goes
        if self.auth.access_token:
            headers = {'Authorization': 'Bearer ' + self.auth.access_token}
        headers.update({'User-Agent': self.user_agent})

        try:
            response = requests.request(method=method, url=self.api_url + endpoint, params=params, files=files,
                                        json=json, data=data, headers=headers, timeout=self.timeout,
                                        verify=self.verify_ssl, stream=stream)

            try:
                response.raise_for_status()
                response_code = response.status_code
                success = True if response_code // 100 == 2 else False
                if response.text:
                    try:
                        data = response.json()
                    except ValueError:
                        data = response.content
                else:
                    data = ''
                return VenariResponse(
                    success=success, response_code=response_code, data=data)

            except ValueError as e:
                return VenariResponse(success=False, message="JSON response could not be decoded {0}.".format(e))
            except requests.exceptions.HTTPError as e:
                if response.status_code == 401:
                    return VenariResponse(
                        message='There was an error handling your request. {} {}'.format(response.content, e),
                        success=False)
        except requests.exceptions.SSLError as e:
            return VenariResponse(message='An SSL error occurred. {0}'.format(e), success=False)
        except requests.exceptions.ConnectionError as e:
            return VenariResponse(message='A connection error occurred. {0}'.format(e), success=False)
        except requests.exceptions.Timeout:
            return VenariResponse(message='The request timed out after ' + str(self.timeout) + ' seconds.',
                                  success=False)
        except requests.exceptions.RequestException as e:
            return VenariResponse(message='There was an error while handling the request. {0}'.format(e),
                                  success=False)


