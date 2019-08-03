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

def scan_web_app(
    url, 
    pattern, 
    workspace_name, 
    template_name, 
    job_name, 
    expected_findings_file):

    api = connect(_master_node_url)
    site_available = site_utils.is_site_available(url, pattern)
    if (not site_available):
        print('site is down')
        return;

    # get the expected baseline findings
    path = str.format('./expected-scan-baselines/{}', expected_findings_file)
    with open(path, mode='r') as file:
        json = file.read()

    start_response = api.start_job_fromtemplate(job_name, workspace_name, template_name)
    if (start_response.error):
        print(start_response.error)
        return;

    job = start_response.job

    while (True):
        job_summary = api.get_job_summary(job.id)
        if (job_summary.status == JobStatus.Completed):
            break
        time.sleep(10)

    compare_result = api.get_scan_compare_data(json, job.uniqueId)



if __name__ == '__main__':
    url = 'https://google-gruyere.appspot.com/679662819249864814433767996093426346573/'
    pattern = ''
    workspace_name = "Cheese"
    template_name = "Exploit"
    job_name = str.format('{} {}', workspace_name, template_name)
    expected_findings_file = "google-gruyere-baseline.json"
    scan_web_app(url, pattern, workspace_name, template_name, job_name, expected_findings_file)
   


