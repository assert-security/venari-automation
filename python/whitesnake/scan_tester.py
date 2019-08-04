from venariapi import VenariAuth, VenariApi
from venariapi.models import JobStatus, JobStartResponse, Job, Workspace, FindingsCompareResultEnum, ScanCompareResultData
from scan import Configuration, ScanTestDefinition
from regression_result import RegressionResult
from typing import List
import venariapi.examples.credentials as creds
import site_utils
import time
import datetime

class ScanTester(object):

    # TODO - single api object and re-connect if needed

    def __init__ (self, master_node_url):
        self._master_node_url = master_node_url


    def _connect(self):
        auth = creds.loadCredentials(self._master_node_url)
        api = VenariApi(auth, self._master_node_url)
        return api


    def is_active_job(self, job:Job):
        ret =  job.status in [JobStatus.Acquired, JobStatus.Ready, JobStatus.Running, JobStatus.Resume]
        return ret


    def stop_existing_scans(self):
        
        try:
            api = self._connect()
            active_jobs = self.get_active_jobs()
            for job in active_jobs:
                api.set_job_status(job.id, JobStatus.Paused)
        
            if (len(active_jobs) > 0):
                start = datetime.datetime.now()
                while True:
                    span = datetime.datetime.now() - start
                    if (span.total_seconds() > 120):
                        return False
                    time.sleep(1)
                    active_job_count = len(self.get_active_jobs())
                    if (active_job_count == 0):
                        return True
        except:
            return False;


    def clear_existing_workspaces(self):
        try:
            api = self._connect()
            workspaces = api.get_workspaces()
            for workspace in workspaces:
                result_data = api.delete_workspace(workspace.id)
                if (not result_data.succeeded):
                    return False

            if (len(workspaces) > 0):
                start = datetime.datetime.now()
                while True:
                    span = datetime.datetime.now() - start
                    if (span.total_seconds() > 120):
                        return False
                    time.sleep(1)
                    workspace_count = len(api.get_workspaces())
                    if (workspace_count == 0):
                        return True
        except:
            return False;


    def start_scans(self, config: Configuration) -> (List[JobStartResponse], dict):
        api = self._connect()
        starts = []

        # create a map of job id to application config
        map_job_start_to_application = {}

        for application in config.tests:
            # unpack the test details
            url = application.endpoint + "/"
            workspace_name = application.workspace
            template_name = application.template_name
            job_name = str.format('{} {}', workspace_name, template_name)
            expected_findings_file = application.expected_findings_file

            # test availability of app to be scanned
            test_url = application.test_url
            pattern = application.test_url_content_pattern
            site_available = site_utils.is_site_available(test_url, pattern)
            if (not site_available):
                print(str.format('failed to start job from template {}: site not available', template_name))

            # try to start the scan if the site is available
            if (site_available):
                start_response = api.start_job_fromtemplate(job_name, workspace_name, template_name)
                if (start_response.error  or start_response.job == None):
                    print(str.format('failed to start job from template {}: {}', template_name, start_response.error))
                else:
                    job = start_response.job
                    map_job_start_to_application[job.id] = application
            else:
                start_response = JobStartResponse(None, "skipped: site not available", false)

            starts.append(start_response)

        return (starts, map_job_start_to_application)


    def monitor_scans(self, starts, config: Configuration, map_job_start_to_application) -> RegressionResult:

        start = datetime.datetime.now()
        api = self._connect()

        # enforce start fail limit
        if (config.scan_start_fail_limit >= 0):
            start_fails = [start for start in starts if (not start.success)]
            start_fail_count = len(start_fails)
            if (start_fail_count > config.scan_start_fail_limit):
                total_seconds = (datetime.datetime.now() - start).total_seconds
                if (start_fail_count > 0):
                    self.stop_existing_scans()
                    error_message = str.format('Failed to start {} jobs:\n\n', start_fail_count)
                    for start_fail in start_fails:
                        if (start_fail.job):
                            error_message += str.format('\tjob name: {}\n\tassigned node: {}\n', job.name, job.assignedNode)
                        else:
                            error_message += str.format('{}\n', start_fail.error)
                
                    return RegressionResult(total_seconds, error_message, [], [], [])

        # enforce site availability fail limit
        if (config.unavailable_app_limit >= 0):
            availability_fails = [start for start in starts if (not start.success)]
            availability_fail_count = len(availability_fails)
            if (availability_fail_count > config.unavailable_app_limit):
                total_seconds = (datetime.datetime.now() - start).total_seconds
                self.stop_existing_scans()
                error_message = str.format('Failed to start {} jobs due to unavailability of test target:\n\n', availability_fail_count)
                for availability_fail in availability_fails:
                    error_message += str.format('{}\n', availability_fail.error)
                
                return RegressionResult(total_seconds, error_message, [], [], [])

        # build a table of started jobs and a table to store completed job diff results
        # values are (job, bool) boolean indicates if it has been processed upon completion
        job_table = {} 

        # values are (job, diff result)
        diffTable = {}

        jobs = [start.job for start in starts if(start.job)]
        for job in jobs:
            job_table[job.id] = (job, False) 
            diffTable[job.id] = None

        # monitor the jobs in the table until all are complete or other abort conditions are hit
        while (True):
            jobs = self.get_all_jobs()
            completed_jobs = [job for job in jobs if (job.status == JobStatus.Completed)]
            for job in completed_jobs:
                if (job.id in job_table and not job_table[job.id]):
                    application = map_job_start_to_application[job.id]
                    diff[job.id] = self.process_completed_job(application)
                    job_table[job.id] = True

            time.sleep(10)


    def process_completed_job(self, application: ScanTestDefinition) -> ScanCompareResultData:
        # get the expected baseline findings
        path = str.format('./expected-scan-baselines/{}', application.expected_findings_file)
        with open(path, mode='r') as file:
            json = file.read()

        # compare the scan on the server node with the expected json representation
        compare_result = api.get_scan_compare_data(json, job.uniqueId)
        return compare_result


    def get_all_jobs(self):
        api = self._connect()
        jobs = []
        query = api.get_jobs() 
        query.execute()
        for job in query.items():
            jobs.append(job)

        return jobs


    def get_active_jobs(self):
        api = self._connect()
        jobs = []
        query = api.get_jobs() 
        query.execute()
        for job in query.items():
            jobs.append(job)

        return [job for job in jobs if(self.is_active_job(job))]



