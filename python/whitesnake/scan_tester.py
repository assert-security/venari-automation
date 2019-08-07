from venariapi import VenariAuth, VenariApi, VenariAuth
from venariapi.models import JobStatus, JobStartResponse, Job, Workspace, FindingsCompareResultEnum, ScanCompareResultData
from scan import Configuration, ScanTestDefinition
from regression_result import RegressionResult
from typing import List
import venariapi.examples.credentials as creds
import site_utils
import time
import datetime
import sys

class ScanTester(object):

    # TODO - single api object and re-connect if needed
    #      - """ help
    #      - enforce max time per job
    #      - integrate new alerts into final analysis of each job
    #      - consolidate various job disposition tables into one application result class for the values

    def __init__ (self, config: Configuration):
        self._config = config
        self._api = None

    def connect(self, auth: VenariAuth):
        self._api = VenariApi(auth, self._config.master_node)

    def is_active_job(self, job: Job):
        ret =  job.status in [JobStatus.Acquired, JobStatus.Ready, JobStatus.Running, JobStatus.Resume]
        return ret

    def stop_existing_scans(self):
        
        start = datetime.datetime.now()
        
        # move all active jobs into cancelled or paused state
        active_jobs = self.get_active_jobs()
        while (len(active_jobs) > 0):
            span = datetime.datetime.now() - start
            if (span.total_seconds() > 120):
                return False

            for job in active_jobs:
                if (not self.finalize_job(job)):
                    return False

            active_jobs = self.get_active_jobs()

        # force complete any paused jobs
        paused_jobs = self.get_jobs_by_status(JobStatus.Paused)
        all_force_completed = True
        for job in paused_jobs:
            has_running_job = True
            while (has_running_job):
                has_running_job = self._api.has_running_job(job.uniqueId, job.assignedNode)
                if (not has_running_job):
                    break

                time.sleep(5)

            result = self._api.force_complete_job(job.uniqueId, job.assignedNode)
            if (not result.succeeded):
                all_force_completed = False

        if (not all_force_completed):
            return False

        active_jobs = self.get_active_jobs()
        while (len(active_jobs) > 0):
            span = datetime.datetime.now() - start
            if (span.total_seconds() > 120):
                return False

        return True

    def finalize_job(self, job: Job):

        start = datetime.datetime.now()
        try:
            if (job.status == JobStatus.Completed or job.status == JobStatus.Failed or job.status == JobStatus.Cancelled):
                    return True
        
            if (job.status == JobStatus.Ready):       
                self._api.set_job_status(job.id, JobStatus.Cancelled)
                return True

            if (job.status == JobStatus.Acquired or job.status == JobStatus.Resume or job.status == JobStatus.Running):       
                self._api.set_job_status(job.id, JobStatus.Paused)
                if (not self._api.wait_for_job_status(job.id, JobStatus.Paused, 60)):
                    return False
                else:
                    return True

            if (job.status == JobStatus.Paused):       

                # pause status is not a reliable indicator that all job internal processing
                # is complete so poll for the has_running_job condition until nothing is running`
                has_running_job = True
                while (has_running_job):
                    has_running_job = self._api.has_running_job(job.uniqueId, job.assignedNode)
                    if (not has_running_job):
                        break
                    time.sleep(5)

                try:
                    return self.try_force_complete(job, 30)
                except:
                    type, value, traceback = sys.exc_info()
                    return False

        finally:
            span = datetime.datetime.now() - start
            print(str.format('finalize ran for {} seconds', span.total_seconds()))


    def clear_workspace(self, workspace):
        result = self._api.delete_workspace(workspace.id)
        if (not result.succeeded):
            return False

        return True


    def clear_existing_workspaces(self):
        try:
            workspaces = self._api.get_workspaces()
            for workspace in workspaces:
                self.clear_workspace(workspace)

            if (len(workspaces) > 0):
                start = datetime.datetime.now()
                while True:
                    span = datetime.datetime.now() - start
                    if (span.total_seconds() > 120):
                        return False
                    workspace_count = len(self._api.get_workspaces())
                    if (workspace_count == 0):
                        break
                    else:
                        workspaces = api.get_workspaces()
                        for workspace in workspaces:
                            self.clear_workspace(workspace)

                    time.sleep(3)
            
            return True
        except:
            return False


    def start_scans(self, config: Configuration) -> (List[JobStartResponse], dict):
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
                start_response = self._api.start_job_fromtemplate(job_name, workspace_name, template_name)
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

        # enforce start fail limit
        start_fails = [start for start in starts if (not start.success)]
        if (config.scan_start_fail_limit >= 0):
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
        availability_fails = [start for start in starts if (not start.success)]
        if (config.unavailable_app_limit >= 0):
            availability_fail_count = len(availability_fails)
            if (availability_fail_count > config.unavailable_app_limit):
                total_seconds = (datetime.datetime.now() - start).total_seconds
                self.stop_existing_scans()
                error_message = str.format('Failed to start {} jobs due to unavailability of test target:\n\n', availability_fail_count)
                for availability_fail in availability_fails:
                    error_message += str.format('{}\n', availability_fail.error)
                
                return RegressionResult(total_seconds, error_message, [], [], [])

        # build tables and lists to track started jobs, diff results and failed jobs
        # values are boolean flag that indicates if it has been processed upon completion
        job_table = {} 
        job_processed_table = {} 

        # values are diff result
        diffTable = {}

        # values are job ID
        failedJobs = []

        jobs = [start.job for start in starts if(start.job)]
        for job in jobs:
            job_table[job.id] = job
            job_processed_table[job.id] = False
            diffTable[job.id] = None

        # monitor the jobs in the table until all are complete or other abort conditions are hit
        while (True):
            # see if all the jobs have landed in a completed or failed state
            active_jobs = [job for job in jobs if self.is_active_job(job)]
            waiting = False
            for job in active_jobs:
                if (job.id in job_processed_table and not job_processed_table[job.id]):
                    waiting = True
                    break

            if (waiting == False):
                break

            jobs = self.get_all_jobs()
            completed_jobs = [job for job in jobs if (job.status == JobStatus.Completed)]
            for job in completed_jobs:
                if (job.id in job_table and not job_table[job.id]):
                    application = map_job_start_to_application[job.id]
                    diff[job.id] = self.process_completed_job(application)
                    job_table[job.id] = True

            failed_jobs = [job for job in jobs if (job.status == JobStatus.Failed)]
            for job in failed_jobs:
                if (job.id in job_table and not job_table[job.id]):
                    failed_jobs.append(job.id)
                    job_table[job.id] = True

            time.sleep(10)

        # build the final result. incorporate passes, completion fails, finding fails, unavailable sites, start fails
        x = 1


    def process_completed_job(self, application: ScanTestDefinition) -> ScanCompareResultData:
        # get the expected baseline findings
        path = str.format('../../../IceDrason/Source/Testing/TestData/automated-regression/expected-scan-baselines/{}', application.expected_findings_file)
        with open(path, mode='r') as file:
            json = file.read()

        # compare the scan on the server node with the expected json representation
        compare_result = self._api.get_scan_compare_data(json, job.uniqueId)
        return compare_result

    def get_job_status(self, job_id: int) -> JobStatus:
        summary = self._api.get_job_summary(job_id)
        return summary.status

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        jobs = []
        query = self._api.get_jobs() 
        query.execute()
        for job in query.items():
            jobs.append(job)

        return [job for job in jobs if(job.status == status)]


    def get_all_jobs(self) -> List[Job]:
        jobs = []
        query = self._api.get_jobs() 
        query.execute()
        for job in query.items():
            jobs.append(job)

        return jobs


    def get_active_jobs(self) -> List[Job]:
        jobs = []
        query = self._api.get_jobs() 
        query.execute()
        for job in query.items():
            jobs.append(job)

        return [job for job in jobs if(self.is_active_job(job))]



