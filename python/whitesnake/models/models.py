from venariapi.models import *
from scan import Configuration, ScanTestDefinition
from enum import IntEnum
from typing import List

class TestExecResult(IntEnum):
    AppNotAvailable = 0,
    ScanStartFail = 1,
    ScanExecuteFail = 2,
    ScanCompleted = 3,
    ComputeCompareDataFailed = 4,


class TestData(object):
    def __init__ (self, 
                  scan_start_data: JobStartResponse,
                  test_definition: ScanTestDefinition = None):
        self.scan_start_data: JobStartResponse = scan_start_data
        self.test_definition: ScanTestDefinition = test_definition
        self.job: Job = None if (not scan_start_data) else scan_start_data.job
        self.test_exec_result: TestExecResult = None
        self.test_exec_error_message = None
        self.scan_processed: bool = False
        self.compare_result: JobCompare = None


class RegressionExecResult(object):
    def __init__ (self, 
                  total_seconds: int,
                  error_message: str,
                  tests: List[TestData]):
        self.total_seconds = total_seconds
        self.error_message = error_message
        self.tests = tests

