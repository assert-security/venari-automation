import typing
import datetime
from  dateutil.parser import parse

class Workspace(object):
    def __init__(self,name:str,id:int,uniqueId:str):
        self.name=name
        self.id:int=id
        self.uniqueId=uniqueId


    @classmethod 
    def FromJson(cls,workspace:dict):
        return cls(
            dict["SummaryData"]["DisplayName"],
            dict["ID"],
            dict["UniqueID"])
            
class Job(object):
    startTime:datetime
    endTime:datetime
    duration:datetime.timedelta

    def __init__(self,
        name:str,
        id:int,
        status,
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
            print(a)
            print(a["StartTime"])
            self.startTime=parse(a["StartTime"])
            self.endTime=parse(a["EndTime"])
            
            if self.endTime.toordinal() != datetime.datetime.min.toordinal():
                self.duration=self.endTime-self.startTime
            else:
                self.duration=0

    @classmethod
    def fromResults(cls,results:dict):
        
        workspaces:dict={}
        for i in results["Workspaces"]:
            w=Workspace(
                i["SummaryData"]["DisplayName"],
                i["ID"],
                i["UniqueID"]
            )
            workspaces[w.id]=w

        jobs=[]
        for i in results["Items"]:
            j:Job=cls(
                i["Name"],
                i["ID"],
                i["Status"],
                i["Activity"],
                i["AssignedTo"],
                workspaces[i["WorkspaceID"]]
            )
            jobs.append(j)

        return jobs
