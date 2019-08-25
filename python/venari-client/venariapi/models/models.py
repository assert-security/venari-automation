import typing
import datetime
from  dateutil.parser import parse
from enum import IntEnum
from venariapi.models.generated_models import *

class Workspace(object):
    def __init__(self,name:str,id:int,unique_id:str,db_data:DBData):
        self.name=name
        self.id:int=id
        self.unique_id = unique_id
        self._db_data:DBData=db_data

    @classmethod 
    def from_data(cls,data:dict):
        summary_data = data["SummaryData"]
        dbid = summary_data["DBData"]["DBID"]
        return cls(
            summary_data["DisplayName"],
            data["ID"],
            data["UniqueID"],
            DBData(dbid, DBType.WorkSpace))

    @property
    def db_data(self)->DBData:
        return self._db_data
            
class Job(object):
    def __init__(self,
        name:str,
        id:int,
        unique_id:str,
        status:JobStatus,
        activity:[],
        assigned_to:str,
        workspace:Workspace):

        self.name=name
        self.status=status
        self.id=id
        self.assigned_to = assigned_to
        self.workspace=workspace
        self._dbData:DBData=None
        self.unique_id = unique_id
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
            self._dbData=DBData(self.unique_id,DBType.Job)
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
        assigned_to:str,
        id:int,
        name:str,
        counts,
        raw:dict,
        status:JobStatus
    ):
        self.assigned_node = assigned_to
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
        severity:Severity,
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


class VerifyEndpointInfo(object):
    def __init__(self,name:str,url:str,search_text:str=None):
        self.name=name
        self.url=url
        self.search_text=search_text
        self.is_up=False
        self.http_status_code=0
        self.failed_reason=None

    def __repr__(self):
        return f"{{name:{self.name},url:{self.url},is_up:{self.is_up},failed_reason:{self.failed_reason}}}"