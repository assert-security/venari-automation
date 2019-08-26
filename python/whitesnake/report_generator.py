from venariapi.models import *
from models import TestData, RegressionExecResult, TestExecResult
from scan import Configuration, ScanTestDefinition
import sys
import os
import site_utils
import file_utils
import time
import datetime
from scan import *
from pathlib import Path
import sys


class ReportGenerator(object):

    def __init__ (self):
        pass

    def generate_report(self, regression_result: RegressionExecResult) -> str:
        if (not regression_result):
            return "empty regression result"

        total_seconds = regression_result.total_seconds
        total_hours = total_seconds // 3600
        remainder_minutes = (total_seconds % 3600) // 60
        time_text = f'{total_hours} hours {remainder_minutes} minutes'

        report = f'regression suite ran for {time_text}\n\n'
        if (regression_result.error_message):
            return regression_result.error_message

        test_fail_count = 0
        test_pass_count = 0
        test_skip_count = 0
        if (len(regression_result.tests) > 0):
            suite_passed = True
            for test in regression_result.tests:
                if (test.test_exec_result == TestExecResult.AppNotAvailable):
                    test_skip_count += 1
                else:
                    passed, message = self.did_scan_pass(test)
                    if (passed):
                        test_pass_count += 1
                    else:
                        test_fail_count += 1

            report += f'PASSED:  {test_pass_count}\n'
            report += f'FAILED:  {test_fail_count}\n'
            report += f'SKIPPED: {test_skip_count}\n\n'

            for test in regression_result.tests:
                try:
                    report += '********************************************************************************\n'
                    report += f'TARGET:              {test.test_definition.name}\n'
                    report += f'MAX MISSING:         {test.test_definition.max_missing_findings}\n'
                    if (test.scan_start_data.job.duration):
                        report += f'DURATION:            {test.scan_start_data.job.duration}\n\n'

                    report += f'BASELINE COMPARISON: {test.compare_result.comparison}\n'
                    report += '********************************************************************************\n\n'
                    display_text = test.compare_result.display_details.replace('\r\n','\n')
                    report += f'{display_text}\n'
                except:
                    pass

        return report


    def did_scan_pass(self, test: TestData) -> (bool, str):
        if (not test.test_definition):
            return (False, "no test definition provided")

        if (not test.compare_result):
            return (False, "empty scan compare result")

        if (not test.scan_processed):
            return (False, "scan not processed on completion")

        if (not test.test_exec_result):
            return (False, "no test execution result set")

        if (not test.scan_start_data):
            return (False, "no scan start result set")

        if (test.test_exec_result == TestExecResult.ScanStartFail):
            return (False, "scan did not start")

        if (test.test_exec_result == TestExecResult.ScanExecuteFail):
            return (False, "scan failed during job run")

        if (test.compare_result.missing_findings_count > test.test_definition.max_missing_findings):
            message = f'{test.compare_result.missing_findings_count} missing findings exceeded limit of {test.test_definition.max_missing_findings}'
            return (False, message)

        return (True, "")


    def write_report(self, report_name: str, report: str):
        output_dir = f'{os.getcwd()}/reports'.replace('\\', '/')
        ensure_output_dir = file_utils.ensure_dir(output_dir)
        if (not ensure_output_dir):
            print('failed to ensure empty output directory')
        else:
            dt_text = datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
            file_path = f'{output_dir}/{report_name}-{dt_text}.txt'
            with open(file_path, mode='w+') as outfile:
                outfile.write(report)






