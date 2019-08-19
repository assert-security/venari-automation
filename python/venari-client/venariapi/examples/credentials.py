import json
from os import path
from venariapi import VenariAuth
from pathlib import Path

def save_credentials(master_url,token_endpoint:str,secret:str,client_id:str,extra:dict):
     credentials:dict={
          'master_url': master_url,
          'token_endpoint':token_endpoint,
          'client_secret':secret,
          'client_id':client_id,
          'extra':extra
     }

     saveFileName=str(Path.home())+'/venari_cli.json'
     urlmap=dict={}
     data=dict=[{}]
     if(path.exists(saveFileName)):
          with open(saveFileName) as infile:
               data = json.load(infile)
          #add/replace existing credentials for master_url
          urlmap={x["master_url"]:x for x in data }

     urlmap[master_url]=credentials

     with open(saveFileName, 'w+') as outfile:  
          #json.dump(list(urlmap.values()), outfile)
          json.dump([obj for obj in urlmap.values()], outfile)

def load_credentials(master_url:str)->VenariAuth:
     resp=None
     file_name=str(Path.home())+'/venari_cli.json'
     if(path.exists(file_name)):
          with open(file_name) as infile:
               data = json.load(infile)
               urlmap={x["master_url"]:x for x in data }
               if(master_url in urlmap):
                    m=urlmap[master_url]
                    resp=VenariAuth.login(
                         m['token_endpoint'],
                         m['client_secret'],
                         m['client_id'],
                         m['extra']
                    )
     return resp
