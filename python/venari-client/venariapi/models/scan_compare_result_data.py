from venariapi.models.findings_compare_result_enum import FindingsCompareResultEnum

class ScanCompareResultData(object):
    def __init__ (self, 
                  compare_result: FindingsCompareResultEnum, 
                  error_message: str, 
                  display_text: str
        ):
            self.error_message = error_message
            self.display_text = display_text
            self.compare_result = compare_result

    @classmethod
    def from_dict(cls, data:dict):
        return cls(
            data['FindingsComparison'],
            data['ErrorMessage'], 
            data['DisplayDetails'])


