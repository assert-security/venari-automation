from venariapi.models import JobStatus
from venariapi import VenariAuth, VenariApi
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

def scan_web_app(url, pattern, workspace_name, template_name, job_name):
    api = connect(_master_node_url)
    site_available = site_utils.is_site_available(url, pattern)
    if (not site_available):
        print('site is down')
        return;

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


if __name__ == '__main__':
    url = 'http://zero.webappsecurity.com'
    pattern = '<title>Zero - Personal Banking - Loans - Credit Cards</title>'
    workspace_name = "Free Bank"
    template_name = "Authenticated Exploit"
    job_name = str.format('{} {}', workspace_name, template_name)
    scan_web_app(url, pattern, workspace_name, template_name, job_name)
   


