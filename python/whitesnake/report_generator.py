from venariapi.models import JobStatus, JobStartResponse, Job, Workspace, FindingsCompareResultEnum, ScanCompareResultData
from models import TestData, RegressionExecResult, TestExecResult
from scan import Configuration, ScanTestDefinition

class ReportGenerator(object):

    def __init__ (self):
        pass

    def generate_report(self, regression_result: RegressionExecResult) -> str:
        return "TODO"