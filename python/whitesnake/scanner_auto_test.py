from venariapi import VenariAuth, VenariApi
from venariapi.models import JobStatus
from venariapi.models.findings_compare_result_enum import FindingsCompareResultEnum
from venariapi.models.scan_compare_result_data import ScanCompareResultData
import venariapi.examples.credentials as creds
import site_utils
import time

class ScannerAutoTest(object):

    def __init__ (self, master_node_url):
        self._master_node_url = master_node_url

    def _connect(self):
        auth = creds.loadCredentials(self._master_node_url)
        api = VenariApi(auth, self._master_node_url)
        return api

    def scan_web_app(
        self,
        url, 
        pattern, 
        workspace_name, 
        template_name, 
        job_name, 
        expected_findings_file):

        api = self._connect()
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



