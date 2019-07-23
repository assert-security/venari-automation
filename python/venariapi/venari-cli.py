#!/usr/bin/env python3
import click
import  getpass
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
     if(not secret):
          secret=getpass.getpass(prompt='client secret:')
     #load authentication info from file if we have it..
     idp=VenariApi.getIdpInfo(ctx.obj.url)
     token_endpoint=VenariApi.getTokenEndpoint(idp.authority)
     auth=VenariAuth.login(token_endpoint,secret,client_id,extra_idp)
     saveCredentials(ctx.obj.url,token_endpoint,secret,client_id,extra_idp)
@cli.group()
def job():
    pass


@job.command()
@click.pass_context
@click.option('--workspace',nargs=1)
def list(ctx,workspace):
     if workspace:
          w=ctx.obj.api.get_workspace_by_name(workspace)
          result = ctx.obj.api.get_jobs_for_workspace(w.data["ID"])
          result.execute(100)
          print ("found {0} jobs".format(result.totalCount))
          while(result.move_next()):
               print(result.data_json(True))
     else:
          result=ctx.obj.api.get_jobs()
          resp=result.executeRaw()
          jobs:List[Job]=Job.fromResults(resp.data)
          print(f"{'Name':35} {'JId':3} {'Status':10} {'Wks Name':12} {'Duration':14} {'Db Id':36} {'Db Type':2}")
          for j in jobs:
               print(f"{j.name:<35} {j.id:3} {str(j.status):<10} {j.workspace.name:<12} {str(j.duration):<14} {j.DbData.id:36} {j.DbData.type:<2}")

@job.command()
@click.pass_context
@click.option('--jobid',nargs=1,required=True)
def summary(ctx,jobid):
     result=ctx.obj.api.get_job_summary(jobid)
     j=JobSummary.from_results(result.data)

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
     print(result.data_json(True))


@cli.group()
def workspace():
    pass

@workspace.command()
@click.pass_context
def list(ctx):
     print(ctx.obj._url)

@cli.group()
def finding():
     pass

@finding.command()
@click.pass_context
@click.option('--jobid',nargs=1,required=True)
def list(ctx,jobid):
     query=ctx.obj.api.get_findings_for_job(jobid)
     resp=query.executeRaw()
     findings:List[Finding]=Finding.fromResults(resp.data)
     print(f"{'Name':<25} {'Severity':10} {'Location':<40} {'P. Location':15} {'P. Name':15} {'Url':30}")
     
     for f in findings:
          print(f"{f.name:25} {str(f.severity):10} {f.location:<40.40} {f.parameter.location:15} {f.parameter.name:15} {f.parameter.url:30}")



def saveCredentials(master_url,token_endpoint:str,secret:str,client_id:str,extra:dict):
     credentials:dict=[{
          'master_url': master_url,
          'token_endpoint':token_endpoint,
          'client_secret':secret,
          'client_id':client_id,
          'extra':extra
     }]

     saveFileName=str(Path.home())+'/venari_cli.json'
     with open(saveFileName, 'w+') as outfile:  
          json.dump(credentials, outfile)

def loadCredentials(master_url:str)->VenariAuth:
     resp=None
     file_name=str(Path.home())+'/venari_cli.json'
     with open(file_name) as infile:
          data = json.load(infile)
          for  m in data:
               if m["master_url"] == master_url:
                    resp=VenariAuth.login(
                         m['token_endpoint'],
                         m['client_secret'],
                         m['client_id'],
                         m['extra']
                    )
     return resp

# @click.command()
# @click.option('--count', default=1, help='number of greetings')
# @click.argument('name')
# def hello(count, name):
#     for x in range(count):
#         click.echo('Hello %s!' % name)

# cli.add_command(login)

if __name__ == '__main__':
     cli(obj={})