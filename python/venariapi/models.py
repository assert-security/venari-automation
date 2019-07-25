import typing
import datetime
from  dateutil.parser import parse
from enum import IntEnum

class DBTypeEnum(IntEnum):
    Global=0
    Job=1
    Workspace=2

class DBData(object):
    def __init__ (self,id,type:DBTypeEnum):
        self.id=id
        self.type=type

    @staticmethod 
    def from_dict(json:dict):
        data=DBData(json["DBID"],json["DBType"])
        return data


class JobStatus(IntEnum):
    Ready=0
    Acquired=1
    Running=2
    Paused=3
    Completed=4
    Resume=5

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
        raw:dict
    ):
        self.assinged_node=assignedNode
        self.finding_counts=counts

    @classmethod
    def from_results(cls,results:dict):
        counts:FindingCount=[]
        stats=results["Statistics"]
        if(stats and stats["FindingCounts"]):
            for c in results["Statistics"]["FindingCounts"]:
                counts.append(FindingCount.from_dict(c))

        return cls(
            results['AssignedTo'],
            stats['ID'],
            "",
            counts,
            results
        )


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