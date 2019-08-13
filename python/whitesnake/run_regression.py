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

if __name__ == '__main__':

    base_test_data_dir = '../../../IceDragon/Source/Testing/automation'
    config = get_config(f'{base_test_data_dir}/.whitesnake.yaml')
    #config = get_config(f'{base_test_data_dir}/.quick-regression-loop.yaml')

    tester = ScanTester(base_test_data_dir, config)

    # connect to the master node
    auth = creds.loadCredentials(config.master_node)
    tester.connect(auth);
    
    # initialize the regression pass
    go = tester.setup_regression()
    
    if (go):
        # create templates for configured tests
        import_templates(config)

        # start/enqueue scan jobs
        test_items = tester.start_scans(config)

        # monitor progress
        regression_result = tester.wait_for_result(test_items, config)

        # generate report
        generator = ReportGenerator()
        report = generator.generate_report(regression_result)
        print(report)

        # write the report as a text file
        output_dir = f'{os.getcwd()}/reports'.replace('\\', '/')
        ensure_output_dir = file_utils.ensure_empty_dir(output_dir)
        if (not ensure_output_dir):
            print('failed to ensure empty output directory')
        else:
            dt_text = datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
            file_path = f'{output_dir}/scan-compare-report-{dt_text}.txt'
            with open(file_path, mode='w+') as outfile:
                outfile.write(report)


