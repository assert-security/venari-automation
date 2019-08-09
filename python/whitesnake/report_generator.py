from venariapi.models import JobStatus, JobStartResponse, Job, Workspace, FindingsCompareResultEnum, ScanCompareResultData
from models import TestItem, RegressionExecResult, TestExecResult
from scan import Configuration, ScanTestDefinition
from regression_result import RegressionResult

class ReportGenerator(object):

    def __init__ (self):

    def generate_report(self, regression_result: RegressionResult) -> str:
        return "TODO"