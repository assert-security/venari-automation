from venari_api.models.db_type_enum import DBTypeEnum

class DBData(object):
    def __init__ (self,id,type:DBTypeEnum):
        self.id=id
        self.type=type

    @staticmethod 
    def from_dict(json:dict):
        data=DBData(json["DBID"],json["DBType"])
        return data