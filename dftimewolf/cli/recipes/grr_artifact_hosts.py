"""DFTimewolf recipe for collecting data from hosts using GRR.

- Collectors collect default artifacts from hosts using GRR
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch

"""
from __future__ import unicode_literals

contents = {
    'name':
        'grr_artifact_hosts',
    'params': {},
    'collectors': [{
        'name': 'GRRArtifactCollector',
        'args': {
            'hosts': '@hosts',
            'flow_id': None,
            'reason': '@reason',
            'grr_server_url': 'http://localhost:8000',
            'grr_auth': ('admin', 'admin'),
            'approvers': [],
            'verbose': True,
            'artifact_list': '@artifact_list',
        },
    }],
    'processors': [{
        'name': 'LocalPlasoProcessor',
        'args': {
            'timezone': None,
            'verbose': True,
        },
    }],
    'exporters': [{
        'name': 'TimesketchExporter',
        'args': {
            'ts_endpoint': '@ts_endpoint',
            'ts_username': '@ts_username',
            'ts_password': '@ts_password',
            'incident_id': '@incident_id',
            'sketch_id': None,
            'verbose': True,
        }
    }],
}

DEFAULT_ARTIFACT_LIST = (
    'AllUsersShellHistory,BrowserHistory,'
    'LinuxLogFiles,AllLinuxScheduleFiles,'
    'LinuxScheduleFiles,ZeitgeistDatabase,'
    'AllShellConfigs')

args = [('hosts', 'Comma-separated list of hosts to process', None),
        ('reason', 'Reason for collection', None), (
            '--artifact_list', 'Comma-separated list of artifacts to fetch',
            DEFAULT_ARTIFACT_LIST)]
