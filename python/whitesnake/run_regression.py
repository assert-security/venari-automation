from venariapi import VenariAuth, VenariApi, VenariAuth
from venariapi.models import JobStatus
import venariapi.examples.credentials as creds
from scan_tester import ScanTester
from report_generator import ReportGenerator
import site_utils
import file_utils
import time
import datetime
from scan import *
from pathlib import Path
import sys
import traceback

if __name__ == '__main__':

    base_test_data_dir = '../../../IceDragon/Source/Testing/automation'
    config = get_config(f'{base_test_data_dir}/.whitesnake.yaml')
    #config = get_config(f'{base_test_data_dir}/.quick-regression-loop.yaml')

    tester = ScanTester(base_test_data_dir, config)

    # connect to the master node
    auth = creds.load_credentials(config.master_node)
    tester.connect(auth);
    
    # initialize the regression pass
    go = tester.setup_regression()
    
    if (go):

        # create templates for configured tests
        import_templates(config)

        # start/enqueue scan jobs
        test_items = tester.start_scans(config)

        # monitor job progress
        regression_result = tester.wait_for_result(test_items, config)

        # generate report
        generator = ReportGenerator()
        report = generator.generate_report(regression_result)
        print(report)
        generator.write_report('scan-compare-report', report)

        # batch retest the scans that failed with missing findings
        retest_items = tester.start_batch_retest_for_failed_jobs(test_items)

        # monitor progress of retest jobs
        retest_result = tester.wait_for_retest_result(retest_items)

        # generate retest report
        report = generator.generate_report(retest_result)
        print(report)
        generator.write_report('retest-compare-report', report)




