from  venariapi.request_helper import RequestHelper
import json

class IdpInfo(object):
    authority=None
    scope=None
    def __init__(self,data:dict):
        self.authority=data["Authority"]
        self.scope=data["Scope"]

class VenariAuth(object):
    def __init__(self,access_token,token_endpoint,client_id,secret,extra:dict):
        self.access_token=access_token
        self.token_endpont=token_endpoint
        self.client_id=client_id
        self.secret=secret
        self.extra=extra
   
    @classmethod
    def login(cls,token_endpoint:str,client_secret:str,client_id:str,extra:dict):
        
        params={
            'grant_type':'client_credentials',
            'client_secret':client_secret,
            'client_id':client_id
        }
        for i in extra:
          params[i[0]]=i[1]

        resp=RequestHelper.request('POST',token_endpoint,data=params)
        if(not resp.success):
            raise Exception(resp.message)
        
        access_token = resp.data['access_token']
        auth=VenariAuth(access_token,token_endpoint,client_id,client_secret,extra)
        return auth
