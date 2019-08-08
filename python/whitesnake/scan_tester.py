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
import os.path


class TestItemData(object):
    def __init__ (self, 
                  scan_start_data: JobStartResponse,
                  scan_processed: bool = False,
                  scan_compare_result: ScanCompareResultData = None,
                  scan_fail: bool = False):
        self.scan_start_data = scan_start_data
        self.job = scan_start_data.job
        self.scan_processed = scan_processed
        self.scan_compare_result = scan_compare_result
        self.scan_fail = scan_fail


class ScanTester(object):

    # TODO - single api object and re-connect if needed
    #      - """ help
    #      - enforce max time per job
    #      - integrate new alerts into final analysis of each job

    def __init__ (self, base_test_data_dir: str, config: Configuration):
        self._base_test_data_dir = base_test_data_dir
        self._scan_baseline_dir = f'{self._base_test_data_dir}/exploit-scan-baselines' 
        self._config = config
        self._api = None


    def connect(self, auth: VenariAuth):
        self._api = VenariApi(auth, self._config.master_node)


    # clean up existing scans and workspaces
    def setup_regression(self):

        # verify data directories exist so we don't get a failure late
        # in the process after scans run
        if (not os.path.exists(self._base_test_data_dir)):
            print(f"test run abandoned: base test data directory '{self._base_test_data_dir}' does not exist")
            return False

        if (not os.path.exists(self._scan_baseline_dir)):
            print(f"test run abandoned: base test data directory '{self._scan_baseline_dir}' does not exist")
            return False

        stopped = self.stop_existing_scans()
        if (not stopped):
            print("test run abandoned: failed to stop pre-existing jobs")
            return False

        cleared = self.clear_existing_workspaces()
        if (not cleared):
            print("test run abandoned: failed to clear existing workspaces")
            return False

        return True

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


    def start_scans(self, config: Configuration) -> List[TestItemData]:
        list = []

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
                start_response = JobStartResponse(None, f"skipped {job_name}: site not available", False)

            test_scan_data = TestItemData(start_response)
            list.append(test_scan_data)

        return list


    def monitor_scans(self, tests: List[TestItemData], config: Configuration) -> RegressionResult:

        # enforce start fail limit
        start_fails = [test for test in tests if (test.scan_start_data.job and not test.scan_start_data.success)]
        if (config.scan_start_fail_limit >= 0):
            start_fail_count = len(start_fails)
            if (start_fail_count > config.scan_start_fail_limit):
                if (start_fail_count > 0):
                    self.stop_existing_scans()
                    error_message = f'Failed to start {start_fail_count} jobs:\n\n'
                    for start_fail in start_fails:
                        if (start_fail.job):
                            error_message += f'\tjob name: {start_fail.job.name}\n\tassigned node: {start_fail.job.assignedNode}\n'
                        else:
                            error_message += f'{start_fail.error}\n'
                
                    return RegressionResult(0, error_message, [], [], [])

        # enforce site availability fail limit
        availability_fails = [test for test in tests if (not test.scan_start_data.job)]
        if (config.unavailable_app_limit >= 0):
            availability_fail_count = len(availability_fails)
            if (availability_fail_count > config.unavailable_app_limit):
                self.stop_existing_scans()
                error_message = f'Failed to start {availability_fail_count} jobs due to unavailability of test target:\n\n'
                for availability_fail in availability_fails:
                    error_message += f'{availability_fail.error}\n'
                
                return RegressionResult(0, error_message, [], [], [])

        # maps job id to test item        
        test_table = {} 
        
        # maps job ids to bool indicating if completed job has been processed
        job_processed_table = {}

        # lists ids of failed jobs
        failed_jobs = []

        jobs = [test.job for test in tests if test.scan_start_data.success]
        tests_with_jobs = [test for test in tests if test.scan_start_data.success]
        for test in tests_with_jobs:
            job = test.job
            job_processed_table[job.id] = False
            test_table[job.id] = test

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

            completed_jobs = self.get_jobs_by_status(JobStatus.Completed)
            for job in completed_jobs:
                if (job.id in job_table and not job_table[job.id]):
                    test = test_table[job.id]
                    test.scan_processed = True
                    test.scan_fail = False
                    test.scan_compare_result = self.process_completed_job(test.application)
                    job_processed_table[job.id] = True

            failed_jobs = self.get_jobs_by_status(JobStatus.Failed)
            for job in failed_jobs:
                test = test_table[job.id]
                test.scan_processed = True
                test.scan_fail = True
                failed_jobs.append(job.id)
                job_processed_table[job.id] = True

            time.sleep(10)

        report = self.build_report(tests)

        # build the final result. incorporate passes, completion fails, finding fails, unavailable sites, start fails


    def process_completed_job(self, application: ScanTestDefinition) -> ScanCompareResultData:
        # get the expected baseline findings
        path = f'{self._scan_baseline_sir}/{application.expected_findings_file}', 
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


    def is_active_job(self, job: Job):
        return  job.status in [JobStatus.Acquired, JobStatus.Ready, JobStatus.Running, JobStatus.Resume]


