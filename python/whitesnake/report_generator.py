from venariapi.models import JobStatus, JobStartResponse, Job, Workspace, FindingsCompareResultEnum, ScanCompareResultData
from models import TestData, RegressionExecResult, TestExecResult
from scan import Configuration, ScanTestDefinition

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
                report = '********************************************************************************\n'
                report += f'TARGET:              {test.test_definition.name} ({test.test_definition.template_name})\n'
                report += f'NODE:                {test.scan_start_data.job.assignedNode}\n'
                report += f'MAX MISSING:         {test.test_definition.max_missing_findings}\n'
                if (test.scan_start_data.job.duration):
                    report += f'DURATION:            {test.scan_start_data.job.duration}\n\n'

                report += f'BASELINE COMPARISON: {str(test.scan_compare_result.compare_result)}\n'
                report = '********************************************************************************\n\n'
                report += f'{test.scan_compare_result.display_text}\n'

        return report


    def did_scan_pass(self, test: TestData) -> (bool, str):
        if (not test.test_definition):
            return (False, "no test definition provided")

        if (not test.scan_compare_result):
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

        if (test.scan_compare_result.missing_findings_count > test.test_definition.max_missing_findings):
            message = f'{test.scan_compare_result.missing_findings_count} missing findings exceeded limit of {test.test_definition.max_missing_findings}'
            return (False, message)

        return (True, "")


