import json
import requests
from venariapi.venari_auth import VenariAuth
from venariapi.request_helper import RequestHelper,VenariResponse

class VenariRequestor(object):
    def __init__(self,auth:VenariAuth,endpoint:str,method:str,verify_ssl=True):
        self.auth=auth
        self.endpoint=endpoint
        self.method=method
        self.verify_ssl=verify_ssl

    def request(self,json=None,params=None)->VenariResponse:
        #add check for auth token expiration and logic to get a new one here.
        ret=RequestHelper.request(method=self.method,authToken=self.auth.access_token,endpoint=self.endpoint,json=json,params=params)
        return ret

