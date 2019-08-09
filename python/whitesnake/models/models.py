from venariapi.models import JobStartResponse, Job, ScanCompareResultData
from scan import Configuration, ScanTestDefinition
from enum import IntEnum
from typing import List

class TestExecResult(IntEnum):
    AppNotAvailable = 0,
    ScanStartFail = 1,
    ScanFail = 2,
    ScanCompleted = 3


class TestData(object):
    def __init__ (self, 
                  scan_start_data: JobStartResponse,
                  test_exec_result: TestExecResult = None,
                  scan_processed: bool = False,
                  scan_compare_result: ScanCompareResultData = None,
                  test_definition: ScanTestDefinition = None):
        self.scan_start_data = scan_start_data
        self.job = None if (not scan_start_data) else scan_start_data.job
        self.scan_processed = scan_processed
        self.scan_compare_result = scan_compare_result
        self.test_exec_result = test_exec_result
        self.test_definition = test_definition


class RegressionExecResult(object):
    def __init__ (self, 
                  total_seconds: int,
                  error_message: str,
                  tests: List[TestData]):
        self.total_seconds = total_seconds
        self.error_message = error_message
        self.tests = tests

