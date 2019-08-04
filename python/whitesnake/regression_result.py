from venariapi.models import JobSummary, ScanCompareResultData
from typing import List
import time
import datetime

class RegressionResult(object):

    def __init__ (self, 
                  total_seconds: int,
                  error_message: str,
                  jobs_completed: List[JobSummary],
                  jobs_skipped: List[str],
                  scan_comparison_results: List[ScanCompareResultData]):
        self.total_seconds = total_seconds
        self.error_message = error_message
        self.jobs_completed = jobs_completed
        self.jobs_skipped = jobs_skipped
        self.scan_comparison_results = scan_comparison_results

