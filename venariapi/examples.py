from venari import *
import json
import sys



def get_jobs_for_workspace(workspaceName):
    w = get_workspace_by_name(workspaceName)
    # print(w)
    txt = w.data_json(True)
    print(txt)
    # print(txt)
    jobs = api.get_jobs_for_workspace(w.data["ID"])
    print(jobs.data_json(True))


def get_workspace_findings(workspaceName):
    w = get_workspace_by_name(workspaceName)
    jobs = api.get_findings_for_workspace(w.data["ID"])


def get_findings_for_workspace(workspaceName):
    w = get_workspace_by_name(workspaceName)
    db = DBData.from_dict(w.data["SummaryData"]["DBData"])
    findings = api.get_findings_for_workspace(db)
    items = (x for x in findings.data['Items'])
    for f in items:
        sd = f["SummaryData"]
        print("{0} [{1}]".format(sd["Name"], sd["Properties"]["location"]))

class TemplateCommand(object):
    def __init__(self,api:VenariApi):
            self.api=api

    def process(self,args):
        #grab the workspace so we can grab it's db id.
        workspace=self.api.get_workspace_by_name(args.workspace)
        db=DBData.from_dict(workspace.data["SummaryData"]["DBData"])

        if(args.list):
            t=self.api.get_templates_for_workspace(db)
            print(t.data_json(True))

class Commands(object):
    def __init__(self):
        parser = argparse.ArgumentParser(prog="examples")
        
        self.sub_parsers=parser.add_subparsers(help='Command help',title="Commands",description="Valid Commands",required=True,dest="command")
        self._build_jobs_parser()
        self._build_workspace_parser()
        self._build_template_parser()
        args=parser.parse_args()
        args.func(args)

    
    def _build_jobs_parser(self):
        subparser=self.sub_parsers.add_parser('job',help="Operations on jobs")
        subparser.set_defaults(func=self.jobs)
        group=subparser.add_mutually_exclusive_group(required=True)
        group.add_argument('--list', action='store_true',help="List all jobs")
        group.add_argument('--workspace', action='store',help="Get job by workspace name")
        self._add_global_args(subparser)        
    
    def _build_workspace_parser(self):
        subparser=self.sub_parsers.add_parser('workspace',help="Operations on workspaces")
        subparser.set_defaults(func=self._workspace)
        group=subparser.add_mutually_exclusive_group(required=True)
        group.add_argument('--list', action='store_true',help="List all workspaces")
        # name needs a value
        group.add_argument('--name', action='store',help="Find workspace by name")
        self._add_global_args(subparser)        
        
    def _build_template_parser(self):
        sub_parser=self.sub_parsers.add_parser('template',help="Operations on templates")
        sub_parser.set_defaults(func=self._template_command)
        group=sub_parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--list',action="store_true")
        group.add_argument('--name',action="store_true")
        sub_parser.add_argument('--workspace',action='store')
        self._add_global_args(sub_parser)        
    def _add_global_args(self,parser):
        #These are all required options, but I found it weird that the arg parser requires them to appear
        #in front of the "command", vs after. This works around that issue.
        parser.add_argument('token_endpoint', type=str, help='Idp Token Endpoint')
        parser.add_argument('api_endpoint', type=str, help='Venari API Endpoint')
        parser.add_argument('--ignore_ssl',action='store_true',help="Don't verify ssl certificates")


    def _init_api(self,args):
        self.auth = VenariAuth(args.token_endpoint)
        self.auth.login_password('admin', 'password')        
        self.api=VenariApi(self.auth,args.api_endpoint,verify_ssl=not args.ignore_ssl)


    def jobs(self,args):
        self._init_api(args)

        if(args.list):
            self.jobs_list()
        elif(args.workspace):
            workspaces=self.api.get_workspace_by_name(args.workspace)
            print(workspaces.data_json(True))

        
    def jobs_list(self):
        jobs = self.api.get_jobs()
        print(jobs.data_json(True))
        

    def _workspace(self,args):
        self._init_api(args)
        if(args.list):
            self.workspace_list()
        elif (args.name):
            self._workspace_name(args.name)


    def _workspace_list(self):
        workspaces=self.api.get_workspaces()
        print(workspaces.data_json(True))

    def _workspace_name(self,name):
        workspaces=self.api.get_workspace_by_name(name)
        print(workspaces.data_json(True))
    
    
    def _template_command(self,args):
        self._init_api(args)
        cmd=TemplateCommand(self.api)
        cmd.process(args)



if __name__ == '__main__':
    
    Commands()


