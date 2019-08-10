from venariapi import VenariAuth, VenariApi, VenariAuth
from venariapi.models import JobStatus, JobStartResponse, Job, Workspace, FindingsCompareResultEnum, ScanCompareResultData
from models import TestData, TestExecResult, RegressionExecResult
from scan import Configuration, ScanTestDefinition
from typing import List
import venariapi.examples.credentials as creds
import site_utils
import time
import datetime
import sys
import os
import os.path
import glob

class ScanTester(object):

    # TODO - single api object and re-connect if needed
    #      - add _ to private methods         
    #      - """ help
    #      - enforce max time per job
    #      - integrate new alerts into final analysis of each job
    #      - save json exports in case we pick up additional findings above baseline
    #      - use logging like in scan.py
    #      - individual pass/fail based on max missing findings
    #      - talk to chris about separate dir for worflows

    def __init__ (self, base_test_data_dir: str, config: Configuration):
        self._base_test_data_dir = base_test_data_dir
        self._scan_baseline_dir = f'{self._base_test_data_dir}/exploit-scan-baselines' 
        self._scan_export_dir = None
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

        self._scan_export_dir = f'{os.getcwd()}/scan-exports'.replace('\\', '/')
        ensure_scan_dir = self.ensure_empty_dir(self._scan_export_dir)
        if (not ensure_scan_dir):
            print('failed to ensure empty scan export directory')
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


    def ensure_empty_dir(self, dir: str):
        if (not os.path.exists(dir)):
            os.mkdir(dir)
            if (not os.path.exists(dir)):
                return False

        path = f'{dir}/*'
        files = glob.glob(path)
        for file in files:
            os.remove(file)

        files = glob.glob(path)
        return True if (len(files) == 0) else False


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
            print(f'finalize ran for {span.total_seconds()} seconds')


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


    def start_scans(self, config: Configuration) -> List[TestData]:
        list = []

        for test_definition in config.tests:
            # unpack the test details
            url = test_definition.endpoint + "/"
            workspace_name = test_definition.workspace
            template_name = test_definition.template_name
            job_name = f'{workspace_name} {template_name}'
            expected_findings_file = test_definition.expected_findings_file

            # test availability of app to be scanned
            test_url = test_definition.test_url
            pattern = test_definition.test_url_content_pattern
            site_available = site_utils.is_site_available(test_url, pattern)
            if (not site_available):
                print(f'failed to start job from template {template_name}: site not available')

            # try to start the scan if the site is available
            test_exec_result = None
            if (site_available):
                start_response = self._api.start_job_fromtemplate(job_name, workspace_name, template_name)
                if (start_response.error  or start_response.job == None):
                    test_exec_result = TestExecResult.ScanStartFail
                    print(f'failed to start job from template {template_name}: {start_response.error}')
            else:
                test_exec_result = TestExecResult.AppNotAvailable
                start_response = None

            test_data = TestData(start_response)
            test_data.test_exec_result = test_exec_result
            test_data.test_definition = test_definition
            list.append(test_data)

        return list


    def wait_for_result(self, tests: List[TestData], config: Configuration) -> RegressionExecResult:

        start = datetime.datetime.now()
        error_message = None

        # enforce start fail limit
        start_fails = [test for test in tests if (test.test_exec_result == TestExecResult.ScanStartFail)]
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
                
                    span = datetime.datetime.now() - start
                    return RegressionExecResult(span.total_seconds(), error_message, tests)

        # enforce site availability fail limit
        availability_fails = [test for test in tests if (test.test_exec_result == TestExecResult.AppNotAvailable)]
        if (config.unavailable_app_limit >= 0):
            availability_fail_count = len(availability_fails)
            if (availability_fail_count > config.unavailable_app_limit):
                self.stop_existing_scans()
                error_message = f'Failed to start {availability_fail_count} jobs due to unavailability of test target:\n\n'
                for availability_fail in availability_fails:
                    error_message += f'{availability_fail.error}\n'
                
                    span = datetime.datetime.now() - start
                    return RegressionExecResult(span.total_seconds(), error_message, tests)

        # maps job id to test item        
        test_table = {} 
        
        tests_with_jobs = [test for test in tests if test.job]
        for test in tests_with_jobs:
            test_table[test.job.id] = test

        # monitor the jobs in the table until all are complete or other abort conditions are hit
        while (True):
    
            # poll for fresh job status (filter by test job ids in case something external started
            # a job that is not associated with the test run
            jobs = [job for job in self.get_all_jobs() if (job.id in test_table)]

            # see if all the jobs have landed in a completed or failed state
            active_jobs = [job for job in self.get_all_jobs() if (job.status not in [JobStatus.Completed, JobStatus.Failed])]
            active_job_count = len(active_jobs)

            completed_jobs = [job for job in jobs if (job.status == JobStatus.Completed)]
            for job in completed_jobs:
                test = test_table[job.id]
                # replace the initial job property now that we have assigned node info
                test.job = job
                if (not test.scan_processed):
                    test.scan_processed = True
                    test.test_exec_result = TestExecResult.ScanCompleted
                    try:
                        test.scan_compare_result = self.process_completed_test(test)
                    except:
                        # TODO - incorporate this in the test data and report
                        pass

            failed_jobs = [job for job in jobs if (job.status == JobStatus.Failed)]
            for job in failed_jobs:
                test = test_table[job.id]
                # replace the initial job property now that we have assigned node info
                test.job = job
                if (not test.scan_processed):
                    test.scan_processed = True
                    test.test_exec_result = TestExecResult.ScanFail

            # break the loop if there are no active jobs
            if (active_job_count == 0):
                break

            time.sleep(10)

        span = datetime.datetime.now() - start
        return RegressionExecResult(span.total_seconds(), error_message, tests)



    def process_completed_test(self, test: TestData) -> ScanCompareResultData:
        # get the expected baseline findings
        path = f'{self._scan_baseline_dir}/{test.test_definition.expected_findings_file}'
        with open(path, mode='r') as file:
            baseline_json = file.read()

        # compare the scan on the server node with the expected json representation
        compare_result = self._api.get_scan_compare_data(baseline_json, test.job.uniqueId, test.job.assignedNode)

        # export the json from the comparison scan
        scan_compare_json = compare_result.comparison_scan_json.replace('\r\n','\n')
        file_base_name = f'{test.test_definition.name}-{str(test.job.uniqueId)}'
        file_path = f'{self._scan_export_dir}/{file_base_name}.json'
        with open(file_path, mode='w+') as outfile:
            outfile.write(scan_compare_json)

        # export any missing findings as a separate json file
        if (compare_result.missing_findings_json and compare_result.missing_findings_json != '[]'):
            missing_findings_json = compare_result.missing_findings_json.replace('\r\n','\n')
            file_path = f'{self._scan_export_dir}/{file_base_name}-missing-findings.json'
            with open(file_path, mode='w+') as outfile:
                outfile.write(missing_findings_json)

        # export any extra findings as a separate json file
        if (compare_result.extra_findings_json and compare_result.extra_findings_json != '[]'):
            extra_findings_json = compare_result.extra_findings_json.replace('\r\n','\n')
            file_path = f'{self._scan_export_dir}/{file_base_name}-extra-findings.json'
            with open(file_path, mode='w+') as outfile:
                outfile.write(extra_findings_json)

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


