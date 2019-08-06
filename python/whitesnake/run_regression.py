from venariapi import VenariAuth, VenariApi, VenariAuth
from venariapi.models import JobStatus
import venariapi.examples.credentials as creds
from scan_tester import ScanTester
import site_utils
import time
from scan import *

if __name__ == '__main__':

    config = get_config()

    tester = ScanTester(config)

    # connect to the master node
    auth = creds.loadCredentials(config.master_node)
    tester.connect(auth);

    # clean up existing scans and wworkspaces
    stopped = tester.stop_existing_scans()
    if (not stopped):
        print("test run abandoned: failed to stop pre-existing jobs")

    cleared = tester.clear_existing_workspaces()
    if (not cleared):
        print("test run abandoned: failed to clear existing workspaces")

    go = stopped and cleared

    if (go):
        # create templates for configured tests
        import_templates(config)

        # enqueue all the scan jobs
        starts, map_job_start_to_config = tester.start_scans(config)

        # monitor progress
        tester.monitor_scans(starts, config, map_job_start_to_config)
   


