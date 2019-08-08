from venariapi import VenariAuth, VenariApi, VenariAuth
from venariapi.models import JobStatus
import venariapi.examples.credentials as creds
from scan_tester import ScanTester
import site_utils
import time
from scan import *
from pathlib import Path

if __name__ == '__main__':

    base_test_data_dir = '../../../IceDragon/Source/Testing/automation'
    config = get_config(f'{base_test_data_dir}/.whitesnake.yaml')

    tester = ScanTester(base_test_data_dir, config)

    # connect to the master node
    auth = creds.loadCredentials(config.master_node)
    tester.connect(auth);
    
    # initialize the regression pass
    go = tester.setup_regression()
    
    if (go):
        # create templates for configured tests
        import_templates(config)

        # start/enqueue scan jobs
        test_items = tester.start_scans(config)

        # monitor progress
        tester.monitor_scans(test_items, config)
   


