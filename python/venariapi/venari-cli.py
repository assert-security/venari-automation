#!/usr/bin/env python3
import click
import  getpass
from os import path
import sys,traceback
from pathlib import Path
from venari import *

class CommonParams:
    url:str=None
    api:VenariApi=None

class OAuthLoginInfo:
     client_id:str
     token_endpoint:str
     client_secret:str

@click.group()
@click.pass_context
@click.option('--url',nargs=1,required=True)
@click.option('--verify_ssl/--no_verify_ssl',default=True)

def cli(ctx,url,verify_ssl):
     #Don't do an init if user is just asking for help.
     if(not "--help" in sys.argv):
          ctx.obj=CommonParams()
          ctx.obj.url=url
          RequestHelper.verify_ssl=verify_ssl
          auth=loadCredentials(url)
          ctx.obj.api=VenariApi(auth,url)

@cli.command()
@click.option('--client_id',nargs=1,required=True)
@click.option('--extra_idp',multiple=True,nargs=2)
@click.option('--secret',nargs=1)
@click.pass_context
def login(ctx,client_id,extra_idp,secret):
     try:
          if(not secret):
               secret=getpass.getpass(prompt='client secret:')
          #load authentication info from file if we have it..
          idp=VenariApi.get_idp_info(ctx.obj.url)
          token_endpoint=VenariApi.get_token_endpoint(idp.authority)
          auth=VenariAuth.login(token_endpoint,secret,client_id,extra_idp)
          saveCredentials(ctx.obj.url,token_endpoint,secret,client_id,extra_idp)
          print("login successful")
     except Exception as e:
          print(f"login failed: {repr(e)}")
          traceback.print_exc(file=sys.stdout)
@cli.group()
def job():
    pass


@job.command()
@click.pass_context
@click.option('--workspace',nargs=1)
def list(ctx,workspace):
     q:None
     if workspace:
          w=ctx.obj.api.get_workspace_by_name(workspace)
          q= ctx.obj.api.get_jobs_for_workspace(w.id)
     else:
          q=ctx.obj.api.get_jobs()

     print(f"{'Name':35} {'JId':3} {'Status':10} {'Wks Name':12} {'Duration':14} {'Db Id':36} {'Db Type':2}")          
     q.execute()
     #print ("found {0} jobs".format(q.total_count))
     for j in q.items():
          print(f"{j.name:<35} {j.id:3} {str(j.status):<10} {j.workspace.name:<12} {str(j.duration):<14} {j.DbData.id:36} {j.DbData.type:<2}")

@job.command()
@click.pass_context
@click.option('--jobid',nargs=1,required=True)
def summary(ctx,jobid):
     j=ctx.obj.api.get_job_summary(jobid)

     print(f"{'Finding Name:':35} {'Count:':6}")
     print(f"{'-'*35:35} {'-'*6:6}")

     for c in j.finding_counts:
          print(f"{c.name:<35} {c.count:>6}")

@job.command()
@click.pass_context
@click.option('--workspace_name',nargs=1,required=True)
@click.option('--name',nargs=1,required=True)
@click.option('--template',nargs=1,required=True)
def start(ctx,workspace_name,name,template):
     result=ctx.obj.api.start_job_fromtemplate(name,workspace_name,template)
     if(result.success):
          print("job created successfully")
     else:
          print(f"job failed to start. Error: {result.error}")


@cli.group()
def workspace():
    pass

@workspace.command()
@click.pass_context
@click.option('--name',nargs=1,help="workspace name")
def list(ctx,name):
     workspaces=[]
     if(name):
          w=ctx.obj.api.get_workspace_by_name(name)
          if(not w is None):
               workspaces.append(w)
     else:
          workspaces=ctx.obj.api.get_workspaces()
     
     print(f"{'Name':10} {'Id':3} {'Db Id':36} {'Db Type':2}")
     for w in workspaces:
          print(f"{w.name:<10} {w.id:<3} {w.db_data.id:<36} {w.db_data.type:<2}")


@cli.group()
def finding():
     pass

@finding.command()
@click.pass_context
@click.option('--jobid',nargs=1,required=True)
def list(ctx,jobid):
     query=ctx.obj.api.get_findings_for_job(jobid)
     print(f"{'Name':<25} {'Severity':10} {'Location':<40} {'P. Location':15} {'P. Name':15} {'Url':30}")
     i=0
     query.execute()
     for f in query.items():
          i=i+1
          print(f"{f.name:25} {str(f.severity):10} {f.location:<40.40} {f.parameter.location:15} {f.parameter.name:15} {f.parameter.url:30}")
     print(f'downloaded {i} findings')

@cli.group()
def template():
     pass

@template.command()
@click.pass_context
@click.option('--workspace',nargs=1,required=True)
def list(ctx,workspace):
     workspace=ctx.obj.api.get_workspace_by_name(workspace)
     templates=ctx.obj.api.get_templates_for_workspace(workspace.db_data)
     print(f"{'Name':<25} {'Id':<3}")
     for t in templates:
          print(f"{t.name:<25} {t.id}")
          pass

def saveCredentials(master_url,token_endpoint:str,secret:str,client_id:str,extra:dict):
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

def loadCredentials(master_url:str)->VenariAuth:
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

if __name__ == '__main__':
     cli(obj={})