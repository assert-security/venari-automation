from venari import *
import json
import sys
import abc
from models import *

class CommandArgProcessor(object):
    def _init_api(self,args):
        self.auth = VenariAuth(args.token_endpoint,verify_ssl=not args.ignore_ssl)
        self.auth.login_password('admin', 'password')        
        self.api=VenariApi(self.auth,args.api_endpoint,verify_ssl=not args.ignore_ssl)
    
    def _add_api_args(self,parser):
        #These are required options that all commands need. If we set them
        #at the top level parser, then the parser exepects them to appear before the command,
        #which we don't want.
        parser.add_argument('token_endpoint', type=str, help='Idp Token Endpoint')
        parser.add_argument('api_endpoint', type=str, help='Venari API Endpoint')
        parser.add_argument('--ignore_ssl',action='store_true',help="Don't verify ssl certificates")

    @abc.abstractmethod
    def proces(self,args):
        print('process')

    def build_commands():
        pass
    def _add_common_args(self,parser):
        pass

class TemplateCommand(CommandArgProcessor):

    def build(self, parent_parser):
        parser=parent_parser.add_parser('template',help="Operations on templates")
        sub_parser=parser.add_subparsers(help='command help',title="Findings Commands")

        list_parser=sub_parser.add_parser('list')
        list_parser.set_defaults(func=self._list_templates)

        list_parser.add_argument('--workspace',action='store')
        self._add_api_args(list_parser)   

    def _list_templates(self,args):
        self._init_api(args)
        #grab the workspace so we can grab its db id.
        workspace=self.api.get_workspace_by_name(args.workspace)
        db=DBData.from_dict(workspace.data["SummaryData"]["DBData"])

        t=self.api.get_templates_for_workspace(db)
        print(t.data_json(True))

class FindingsCommands(CommandArgProcessor):
    def build(self,sub_parsers):
        #add list processor
        parser=sub_parsers.add_parser('finding',help="Findings operations")
        subparser=parser.add_subparsers(help='command help',title="Findings Commands")
        #list command
        list_parser=subparser.add_parser('list')
        list_parser.set_defaults(func=self.list_findings)
        group=list_parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--workspace',action='store')
        group.add_argument('--jobid',action='store')
        
        super()._add_api_args(list_parser)

    def list_findings(self,args):
        self._init_api(args)

        if(not args.workspace):
            #list by workspace
            query=self.api.get_findings_for_job(args.jobid)
        else:
            w=self.api.get_workspace_by_name(args.workspace)
            db = DBData.from_dict(w.data["SummaryData"]["DBData"])
            query=self.api.get_findings_for_workspace(db)
        
        query.execute()
        while(query.move_next()):
            print(query.data_json(True))

class JobCommands(CommandArgProcessor):
                
    def build(self,sub_parsers):
        #add list processor
        jobs_parser=sub_parsers.add_parser('job',help="Jobs operations")
        jobs_subparser=jobs_parser.add_subparsers(help='command help',title="Job Commands")
        #list command
        list_parser=jobs_subparser.add_parser('list')
        list_parser.set_defaults(func=self.list_jobs)
        list_parser.add_argument('--workspace')
        super()._add_api_args(list_parser)
        #start command
        start_parser=jobs_subparser.add_parser('start')
        start_parser.set_defaults(func=self.start_job)
        start_parser.add_argument("jobName",help="Name of new job")
        start_parser.add_argument("workspaceName",help="Workspace store job")
        start_parser.add_argument("templateName",help="Workspace template to start the job with")
        super()._add_api_args(start_parser)

        #summary command
        summary_parser=jobs_subparser.add_parser('summary')
        summary_parser.set_defaults(func=self.job_summary)
        summary_parser.add_argument("id",help="The unique identifier for the job")
        super()._add_api_args(summary_parser)


    def list_jobs(self,args)   :
        self._init_api(args)
        if(args.workspace):
            w=self.api.get_workspace_by_name(args.workspace)
            result = self.api.get_jobs_for_workspace(w.data["ID"])
            result.execute(100)
            print ("found {0} jobs".format(result.totalCount))
            while(result.move_next()):
                print(result.data_json(True))
        else:
            result = self.api.get_jobs()
            # result.execute(100)
            # print ("found {0} jobs".format(result.totalCount))
            # while(result.move_next()):
            #     print(result.data_json(True))

            resp=result.executeRaw()
            # print(resp.data)
            jobs=Job.fromResults(resp.data)
            for j in jobs:
                print(f"Name: {j.name},Id: {j.id},Status: {j.status},Workspace: {j.workspace.name},duration: {j.duration},start:{j.startTime},end:{j.endTime}")

    def start_job(self,args):
        self._init_api(args)
        result=self.api.start_job_fromtemplate(args.jobName,args.workspaceName,args.templateName)
        print(result.data_json(True))
    
    def job_summary(self,args):
        self._init_api(args)
        result=self.api.get_job_summary(args.id)
        print(result.data_json(True))

class WorkspaceCommand(CommandArgProcessor):
    def build(self,parent_parser):
        #add list processor
        workspace_parser=parent_parser.add_parser('workspace',help="Workspace operations")
        workspace_subparser=workspace_parser.add_subparsers(help='command help',title="Workspace Commands")
        #list command
        list_parser=workspace_subparser.add_parser('list')
        list_parser.set_defaults(func=self.list)
        list_parser.add_argument('--name',help="Name of workspace to list")
        super()._add_api_args(list_parser)
    
    def list(self,args):
        self._init_api(args)
        if(args.name):
            workspaces=self.api.get_workspace_by_name(args.name)
            print(workspaces.data_json(True))
        else:
            workspaces=self.api.get_workspaces()
            print(workspaces.data_json(True))


class Commands(object):
    def __init__(self):
        parser = argparse.ArgumentParser(prog="examples")
        
        self.sub_parsers=parser.add_subparsers(help='Command help',title="Commands",description="Valid Commands",required=True,dest="command")

        self.job_commands=JobCommands()
        self.job_commands.build(self.sub_parsers)

        self.findings_command=FindingsCommands()
        self.findings_command.build(self.sub_parsers)

        self.template_command=TemplateCommand()
        self.template_command.build(self.sub_parsers)

        self.workspace_command=WorkspaceCommand()
        self.workspace_command.build(self.sub_parsers)

        args=parser.parse_args()
        args.func(args)
    
 
       
  

  
  

if __name__ == '__main__':
    
    Commands()


