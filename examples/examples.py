import json

from venariapi.venari import VenariApi,VenariAuth,DBData,Finding

auth=VenariAuth('https://host.docker.internal:9002')
api_endpoint='https://host.docker.internal:9000'

api= VenariApi(auth,api_endpoint,verify_ssl=False)
def init():
    # initializing standalone api
    auth.login_password('admin','password')

def get_workspaces():
    init()
    response=api.get_workspaces()
    print(response)
    return response

def get_workspace_by_name(workspaceName):
    init()
    response=api.get_workspace_by_name(workspaceName)
    #print(response)
    return response



def get_jobs_for_workspace(workspaceName):
    w=get_workspace_by_name(workspaceName)
    #print(w)
    txt=w.data_json(True)
    print(txt)
    #print(txt)
    jobs=api.get_jobs_for_workspace(w.data["ID"])
    print(jobs.data_json(True))

def get_workspace_findings(workspaceName):
    w=get_workspace_by_name(workspaceName)
    jobs=api.get_findings_for_workspace(w.data["ID"])

def get_findings_for_workspace(workspaceName):
    w=get_workspace_by_name(workspaceName)
    db=DBData.from_dict(w.data["SummaryData"]["DBData"])
    findings=api.get_findings_for_workspace(db)
    items = (x for x in findings.data['Items'])
    for f in items:
        sd=f["SummaryData"]
        print("{0} [{1}]".format(sd["Name"],sd["Properties"]["location"]))

