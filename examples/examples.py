import json
from venariapi.venari import VenariApi,VenariAuth
auth=VenariAuth('https://host.docker.internal:9002')
api_endpoint='https://host.docker.internal:9000'

api= VenariApi(auth,api_endpoint,verify_ssl=False)
def init():
    # initializing standalone api
    auth.login_password('admin','password')

def getWorkspaces():
    init()
    response=api.get_workspaces()
    print(response)
    return response

def getWorkspaceByName(workspaceName):
    init()
    response=api.get_workspace_by_name(workspaceName)
    #print(response)
    return response
    

def getJobsForWorkspace(workspaceName):
    w=getWorkspaceByName(workspaceName)
    #print(w)
    txt=w.data_json(True)
    print(txt)
    #print(txt)
    jobs=api.get_jobs_for_workspace(w.data["ID"])
    print(jobs.data_json(True))


