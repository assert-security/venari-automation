from venariapi import VenariAuth, VenariApi
from venariapi.models import JobStatus
from venariapi.models.findings_compare_result_enum import FindingsCompareResultEnum
from venariapi.models.scan_compare_result_data import ScanCompareResultData
import venariapi.examples.credentials as creds
from scanner_auto_test import ScannerAutoTest
import site_utils
import time


if __name__ == '__main__':
    master_node_url = 'https://host.docker.internal:9000'
    url = 'https://google-gruyere.appspot.com/679662819249864814433767996093426346573/'
    pattern = ''
    workspace_name = "Cheese"
    template_name = "Exploit"
    job_name = str.format('{} {}', workspace_name, template_name)
    expected_findings_file = "google-gruyere-baseline.json"
    
    scannerTester = ScannerAutoTest(master_node_url)
    scannerTester.scan_web_app(url, pattern, workspace_name, template_name, job_name, expected_findings_file)
   


