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
from venariapi import __version__ as version


class VenariApi(object):
    def __init__(self, api_url, token_url, username=None, password=None, verify_ssl=True, timeout=60, user_agent=None,
                 token=None, client_version='1.0'):
        self.api_url = api_url
        self.token_url = token_url
        self.grant_type = 'password'
        self.client_id = 'venari'
        self.username = username
        self.password = password
        self.token = token
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.client_version = client_version

        if not user_agent:
            self.user_agent = 'venari_api/' + version
        else:
            self.user_agent = user_agent

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Set auth_type based on what's been provided
        if self.token is not None:
            self.auth_type = 'authenticated'
        elif self.token is None:
            self.auth_type = 'authenticate'
        else:
            self.auth_type = 'unauthenticated'

    def get_access_token(self):
        """
        Used for obtaining an oauth access token from the OpenId node to impersonate a user
        :param: grant_type, client_id, username, password
        :return: access_token
        """
        endpoint = '/connect/token'
        data = dict(
            username=self.username,
            password=self.password,
            client_id=self.client_id,
            grant_type=self.grant_type
            )
        return self._request('POST', endpoint, data=data)

    def get_job_listing(self):
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

    def get_scan_results(self):
        """
        :param:
        :return:
        """
        json_data = dict(

        )
        endpoint = ''
        return self._request('POST', endpoint, json=json_data)

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
        if self.token:
            headers = {'Authorization': 'Bearer ' + self.token}
        headers.update({'User-Agent': self.user_agent})

        try:
            if self.auth_type == 'authenticated':
                response = requests.request(method=method, url=self.api_url + endpoint, params=params, files=files,
                                            json=json, data=data, headers=headers, timeout=self.timeout,
                                            verify=self.verify_ssl, stream=stream)

            elif self.auth_type == 'authenticate':
                response = requests.request(method=method, url=self.token_url + endpoint, params=params, json=json,
                                            data=data, headers=headers, timeout=self.timeout, verify=self.verify_ssl)
            else:
                response = requests.request(method=method, url=self.api_url, params=params, files=files,
                                            headers=headers, json=json, data=data, timeout=self.timeout,
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


class VenariResponse(object):
    """Container for all Venari API responses, even errors."""

    def __init__(self, success, message='OK', response_code=-1, data=None):
        self.message = message
        self.success = success
        self.response_code = response_code
        self.data = data

    def __str__(self):
        if self.data:
            return str(self.data)
        else:
            return self.message

    def data_json(self, pretty=False):
        """Returns the data as a valid JSON string."""
        if pretty:
            return json.dumps(self.data, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            return json.dumps(self.data)
