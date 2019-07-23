from venari_requestor import *
from models import *

class VenariQueryResult(object):
    requestor:VenariRequestor=None
    response:VenariResponse=None
    def __init__(self,requestor:VenariRequestor,props:dict):
        self.properties:dict=props
        self.requestor:VenariRequestor=requestor
        self.numPerPage:int=10
        self.curIndex:int=0
        self._totalCount:int=0 #total count of items
        self.curPageCountL:int=0 #number of items in this page

    @property
    def totalCount(self):
        return self._totalCount
    
    def execute(self,numPerPage=100):
        self.properties["Take"]=numPerPage
        self.properties["Skip"]=0
        self.response=self.requestor.request(json=self.properties)
        self._totalCount=self.response.data["TotalCount"]
        self.curPageCount=self.response.data["Count"]
        self.curIndex=-1
        self.properties["QueryID"]=self.response.data["QueryID"]
    
    def executeRaw(self,numPerPage=100):
        self.properties["Take"]=numPerPage
        self.properties["Skip"]=0
        return self.requestor.request(json=self.properties)

    def move_next(self)->bool:
        print("curIndex: {0} page count: {1} total count: {2}".format(self.curIndex,self.curPageCount,self._totalCount))
        if(self.response):
            if(self.curIndex < self.curPageCount-1):
                #we set curIndex to -1 on the initial move_next() so that caller can call execute() and then move_next() immediately, but still be
                #at the first record. This makes the iteration loop a little smaller.
                self.curIndex+=1
                return True
            elif self.properties["Skip"]+self.curIndex+1 >=self._totalCount:
                print ("No more data")
                return False
            else:
                print ("loadng new page")
                #need to load next page of data.
                self.properties["Skip"]+=self.curPageCount
                self.response=self.requestor.request(self.method,self.endpoint,json=self.properties)

                #store new query id if we got one
                self.properties["QueryID"]=self.response.data["QueryID"]
                #index is zero since we just loaded new data and caller must be able to immediately access the new data
                #after this method completes.
                self.curIndex=0
                self.curPageCount=self.response.data["Count"]
                #update our total count in case it changed
                self._totalCount=self.response.data["TotalCount"]
                return True
        return False
    def data(self):
        return self.response.data["Items"][self.curIndex]
    def data_json(self, pretty=False):
        """Returns the data as a valid JSON string."""
        if pretty:
            return json.dumps(self.data(), sort_keys=True, indent=4, separators=(',', ': '))
        else:
            return json.dumps(self.data())
