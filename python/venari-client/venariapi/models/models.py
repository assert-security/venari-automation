import typing
import datetime
from  dateutil.parser import parse
from enum import IntEnum
from venariapi.models.db_data import DBData
from venariapi.models.db_type_enum import DBTypeEnum

class JobStatus(IntEnum):
    Ready=0
    Acquired=1
    Running=2
    Paused=3
    Completed=4
    Resume=5
    Failed=6
    Cancelled=7


    def __str__(self):
        return '%s' % self.name

class Workspace(object):
    def __init__(self,name:str,id:int,uniqueId:str,db_data:DBData):
        self.name=name
        self.id:int=id
        self.uniqueId=uniqueId
        self._db_data:DBData=db_data

    @classmethod 
    def from_data(cls,data:dict):
        summary_data=data["SummaryData"]
        return cls(
            summary_data["DisplayName"],
            data["ID"],
            data["UniqueID"],
            DBData(summary_data["DBData"]["DBID"],DBTypeEnum.Workspace))

    @property
    def db_data(self)->DBData:
        return self._db_data
            
class Job(object):
    def __init__(self,
        name:str,
        id:int,
        uniqueId:str,
        status:JobStatus,
        activity:[],
        assignedNode:str,
        workspace:Workspace):

        self.name=name
        self.status=status
        self.id=id
        self.assignedNode=assignedNode
        self.workspace=workspace
        self._dbData:DBData=None
        self.uniqueId=uniqueId
        a=None
        self.duration=0
        if(activity and len(activity) > 0):
            a=activity[0]
        if a:
            self.startTime=parse(a["StartTime"])
            if(a["EndTime"]):
                self.endTime=parse(a["EndTime"])
            else:
                self.endTime=datetime.datetime.min

            if self.endTime.toordinal() != datetime.datetime.min.toordinal():
                self.duration=self.endTime-self.startTime
            else:
                self.duration=0

    @classmethod
    def from_data(cls,data:dict,workspace:Workspace=None):
        return cls(
                data["Name"],
                data["ID"],
                data["UniqueID"],
                JobStatus(data["Status"]),
                data["Activity"],
                data["AssignedTo"],
                workspace
        )

    @property
    def DbData(self)->DBData:
        if self._dbData==None:
            self._dbData=DBData(self.uniqueId,DBTypeEnum.Job)
        return self._dbData

class FindingCount(object):
    def __init__(self,Count:int,Name:str,Severity:str):
        self.count=Count
        self.name=Name
        self.severity=Severity

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

class JobSummary(object):
    def __init__(
        self,
        assignedNode:str,
        id:int,
        name:str,
        counts,
        raw:dict,
        status:JobStatus
    ):
        self.assigned_node = assignedNode
        self.finding_counts = counts
        self.status = status

    @classmethod
    def from_results(cls, results:dict):
        counts:FindingCount = []
        stats = results["Statistics"]
        if (stats):
            finding_counts = stats["FindingCounts"]
            if (finding_counts):
                for c in finding_counts:
                    counts.append(FindingCount.from_dict(c))

        id = None
        if (stats and stats['ID']):
            id = stats['ID']

        assigned_to = results['AssignedTo']
        status = JobStatus(results['Status'])

        return cls(assigned_to, id, "", counts, results, status)

class FindingSeverity(IntEnum):
    Critical=0
    High=1
    Medium=2
    Low=3
    Info=4
    
    def __str__(self):
        return '%s' % self.name

class FindingParameter(object):
    location:str
    name:str
    value:str
    url:str=None

    @classmethod
    def fromData(cls,data:dict):
        f=cls()
        f.location=data["parameterlocation"]
        f.name=data["parametername"]
        f.value=data["parametervalue"]
        if "url" in data:
            f.url=data["url"]
        else:
            f.url=""
        return f

class Finding(object):
    def __init__(
        self,
        id:int,
        name:str,
        location:str,
        severity:FindingSeverity,
        parameter:FindingParameter
    ):
        self.id=id
        self.name=name
        self.location=location
        self.severity=severity
        self.parameter=parameter

    @classmethod
    def from_data(cls,data:dict):
        summary=data["SummaryData"]
        props=summary["Properties"]
        return cls(
            data["ID"],
            summary["Name"],
            props["location"],
            FindingSeverity(summary["Severity"]),
            FindingParameter.fromData(props)
        )

class JobTemplate(object):
    def __init__(
        self,
        created_time,
        id:int,
        name:str,
        settings_id:int,
        settings_type:int,
        settings_type_display_name:str,
        unique_id:str,
        version:int
    ):
        self.created_time=created_time
        self.id=id
        self.name=name
        self.settings_id=settings_id
        self.settings_type=settings_type
        self.settings_type_display_name=settings_type_display_name
        self.unique_id=unique_id
        self.version=version


    @classmethod
    def from_data(cls,data:dict):
        created_time=parse(data["CreatedAt"])
        return cls(
            created_time,
            data["ID"],
            data["Name"],
            data["SettingsID"],
            data["SettingsType"],
            data["SettingsTypeDisplayName"],
            data["UniqueID"],
            data["Version"]
        )

class JobStartResponse(object):
    def __init__(
        self,
        job:Job,
        error:str,
        success:bool
    ):
        self.job=job
        self.error=error
        self.success=success
    @classmethod
    def from_data(cls,data:dict):
        success:bool=data["Succeeded"]
        if(success):
            job=Job.from_data(data["Job"])
            return cls(job,None,True)
        else:
            return cls(None,data["Message"],False)

class FindingsCompareResultEnum(IntEnum):
    Same = 0
    MissingFindings = 1,
    ExtraFindings = 2,
    MissingAndExtraFindings = 3

class FindingsSummaryCompareData(object):
    def __init__ (self, 
                  compare_result: FindingsCompareResultEnum, 
                  error_message: str, 
                  comparison_scan_json: str,
                  missing_findings_json: str,
                  extra_findings_json: str,
                  missing_findings_count: int,
                  extra_findings_count: int,
                  display_text: str
        ):
            self.compare_result = compare_result
            self.error_message = error_message
            self.comparison_scan_json = comparison_scan_json
            self.missing_findings_json = missing_findings_json
            self.extra_findings_json = extra_findings_json
            self.missing_findings_count = missing_findings_count
            self.extra_findings_count = extra_findings_count
            self.display_text = display_text

    @classmethod
    def from_dict(cls, data:dict):
        return cls(
            FindingsCompareResultEnum(data['FindingsComparison']),
                                      data['ErrorMessage'], 
                                      data['ComparisonScanJSON'],
                                      data['MissingFindingsJSON'],
                                      data['ExtraFindingsJSON'],
                                      int(data['MissingFindingsCount']),
                                      int(data['ExtraFindingsCount']),
                                      data['DisplayDetails'])


class FindingsDetailCompareData(object):
    def __init__ (self, 
                  compare_result: FindingsCompareResultEnum, 
                  error_message: str, 
                  workspace_id: str,
                  download_file_id: str,
                  missing_findings_count: int,
                  extra_findings_count: int,
                  display_text: str
        ):
            self.compare_result = compare_result
            self.error_message = error_message
            self.workspace_id = workspace_id
            self.download_file_id = download_file_id
            self.missing_findings_count = missing_findings_count
            self.extra_findings_count = extra_findings_count
            self.display_text = display_text

    @classmethod
    def from_dict(cls, data:dict):
        return cls(
            FindingsCompareResultEnum(data['FindingsComparison']),
                                      data['ErrorMessage'], 
                                      data['WorkspaceID'], 
                                      data['DownloadFileID'], 
                                      int(data['MissingFindingsCount']),
                                      int(data['ExtraFindingsCount']),
                                      data['DisplayDetails'])



class OperationResultData(object):
    def __init__ (self, 
                  succeeded: bool, 
                  message: str, 
        ):
            self.succeeded = succeeded
            self.message = message

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['Succeeded'], data['Message'])
