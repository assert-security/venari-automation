import typing
import datetime
from  dateutil.parser import parse
from enum import IntEnum

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


    @classmethod 
    def fromData(cls,data:dict):
        return cls(
            data["SummaryData"]["DisplayName"],
            data["ID"],
            data["UniqueID"])
            
class Job(object):
    startTime:datetime
    endTime:datetime
    duration:datetime.timedelta

    def __init__(self,
        name:str,
        id:int,
        status:JobStatus,
        activity:[],
        assignedNode:str,
        workspace:Workspace):

        self.name=name
        self.status=status
        self.id=id
        self.assignedNode=assignedNode
        self.workspace=workspace

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
