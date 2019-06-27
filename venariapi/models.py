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
    def __init__(self,name:str,id:int,uniqueId:str):
        self.name=name
        self.id:int=id
        self.uniqueId=uniqueId
        self._dbData:DBData=None

    @classmethod 
    def fromData(cls,data:dict):
        return cls(
            data["SummaryData"]["DisplayName"],
            data["ID"],
            data["UniqueID"])

    @property
    def DbData(self)->DBData:
        if self._dbData==None:
            self._dbData=DBData(self.uniqueId,DBTypeEnum.Workspace)
        return self._dbData

    @classmethod
    def fromResults(cls,results):
        workspaces=[]
        for i in results:
            workspaces.append(Workspace.fromData(i))
        return workspaces

            
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

        if(len(activity) > 0):
            a=activity[0]
        if a:
            self.startTime=parse(a["StartTime"])
            self.endTime=parse(a["EndTime"])
            
            if self.endTime.toordinal() != datetime.datetime.min.toordinal():
                self.duration=self.endTime-self.startTime
            else:
                self.duration=0

    @classmethod
    def fromData(cls,data:dict,workspace:Workspace):
        return cls(
                data["Name"],
                data["ID"],
                data["UniqueID"],
                JobStatus(data["Status"]),
                data["Activity"],
                data["AssignedTo"],
                workspace
        )
        
    
    @classmethod
    def fromResults(cls,results:dict):
        
        workspaces:dict={}
        for i in results["Workspaces"]:
            w=Workspace.fromData(i)
            workspaces[w.id]=w

        jobs=[]
        for i in results["Items"]:
            j=Job.fromData(i,workspaces[i["WorkspaceID"]])
            jobs.append(j)
        return jobs

    @property
    def DbData(self)->DBData:
        if self._dbData==None:
            self._dbData=DBData(self.uniqueId,DBTypeEnum.Job)
        return self._dbData

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
    def fromData(cls,data:dict):
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
    def fromResults(cls,data:dict):
        findings=[]
        for i in data["Items"]:
            f=Finding.fromData(i)
            findings.append(f)
        return findings


