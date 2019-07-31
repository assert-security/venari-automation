from enum import IntEnum,Enum

from venariapi.models import JobStatus

class TestState(Enum):
    pass 


class ScanTestDefinition(object):
    def __init__(self,name:str,endpoint:str):
        self.name=name
        self.endpoint=endpoint

if __name__ == '__main__':
     v:JobStatus=JobStatus.Completed
     print(v)
     