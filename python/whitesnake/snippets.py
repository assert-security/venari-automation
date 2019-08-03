from venariapi import VenariAuth, VenariApi
from venariapi.models import JobStatus
from venariapi.models.findings_compare_result_enum import FindingsCompareResultEnum
from venariapi.models.scan_compare_result_data import ScanCompareResultData
import venariapi.examples.credentials as creds
import site_utils
import time

_master_node_url = 'https://host.docker.internal:9000'

def connect(master_node_url):
    auth = creds.loadCredentials(master_node_url)
    api = VenariApi(auth, master_node_url)
    return api

def list_jobs():
    api = connect(_master_node_url)
    message = '\n\n'
    workspaces = api.get_workspaces()
    for workspace in workspaces:
        message +=  str.format('\n{}\n', workspace.name)
        query = api.get_jobs_for_workspace(workspace.id) 
        query.execute()
        for job in query.items():
            message += str.format('\n\t{} ({})\n', job.name, job.status.name)
            findings_query = api.get_findings_for_job(job.uniqueId)
            findings_query.execute()
            for finding in findings_query.items():
                message += str.format('\t\tfinding:  {} ({})\n', finding.name, finding.severity.name)

    message += '\n'
    print(message)


if __name__ == '__main__':
    list_jobs()   


