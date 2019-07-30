import json
from venari_api.venari_requestor import VenariRequestor,VenariResponse
from venari_api.models import Workspace,Job,Finding

class VenariQuery(object):
    default_page_size:int=100
    def __init__(self,requestor:VenariRequestor,props:dict):
        self.properties:dict=props
        self.requestor:VenariRequestor=requestor
        self.numPerPage:int=10
        self.curIndex:int=0
        self._totalCount:int=0 #total count of items
        self.curPageCountL:int=0 #number of items in this page
        self.response:VenariResponse=None

    @property
    def total_count(self):
        return self._totalCount
    
    def execute(self,numPerPage=default_page_size):
        self.properties["Take"]=numPerPage
        self.properties["Skip"]=0
        self.curIndex=-1

        self.response=self.requestor.request(json=self.properties)
        self.properties["QueryID"]=self.response.data["QueryID"]
        self.curPageCount=self.response.data["Count"]
        self._totalCount=self.response.data["TotalCount"]

    def items(self):
        while(self.__move_next()):
            yield self.data()

    def __move_next(self)->bool:
        # print("curIndex: {0} page count: {1} total count: {2}".format(self.curIndex,self.curPageCount,self._totalCount))
        if(self.response):
            if(self.curIndex < self.curPageCount-1):
                #we set curIndex to -1 on the initial __move_next() so that caller can call execute() and then __move_next() immediately, but still be
                #at the first record. This makes the iteration loop a little smaller.
                self.on_page_load()
                self.curIndex+=1
                return True
            elif self.properties["Skip"]+self.curIndex+1 >=self._totalCount:
                return False
            else:
                #print ("loading new page")
                #need to load next page of data.
                self.properties["Skip"]+=self.curPageCount
                self.response=self.requestor.request(json=self.properties)

                #store new query id if we got one
                self.properties["QueryID"]=self.response.data["QueryID"]
                #index is zero since we just loaded new data and caller must be able to immediately access the new data
                #after this method completes.
                self.curIndex=0
                self.curPageCount=self.response.data["Count"]
                #update our total count in case it changed
                self._totalCount=self.response.data["TotalCount"]
                self.on_page_load()
                return True
        return False

    def on_page_load(self):
        pass

    def data(self):
        return self.response.data["Items"][self.curIndex]

    def data_json(self, pretty=False):
        """Returns the data as a valid JSON string."""
        if pretty:
            return json.dumps(self.data(), sort_keys=True, indent=4, separators=(',', ': '))
        else:
            return json.dumps(self.data())
    def get_current_item(self):
        return self.response.data["Items"][self.curIndex]

class JobQuery(VenariQuery):

    def __init__(self,requestor:VenariRequestor,props:dict):
        VenariQuery.__init__(self,requestor,props)

    def on_page_load(self):
        #each page gets a set of workspaces that need to be parsed and hooked up to each job
        #as each job object is created through iteration.
        self.workspaces= {x["ID"]:Workspace.from_data(x) for x in self.response.data["Workspaces"]}

    def data(self)->Job:
        curItem=self.get_current_item()
        return Job.from_data(curItem,self.workspaces[curItem["WorkspaceID"]])

class FindingQuery(VenariQuery):
    def __init__(self,requestor:VenariRequestor,props:dict):
        VenariQuery.__init__(self,requestor,props)
    
    def data(self)->Finding:
        curItem=self.get_current_item()
        return Finding.from_data(curItem)
