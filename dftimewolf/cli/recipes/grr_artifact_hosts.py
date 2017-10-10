"""Timeflow recipe for collecting data from hosts using GRR.

- Collectors collect default artifacts from hosts using GRR
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch

"""

__author__ = u'tomchop@google.com (Thomas Chopitea)'


contents = {
    'name': 'grr_artifact_hosts',
    'params': {},
    'collectors': [
        {
            'name': 'GRRArtifactCollector',
            'args': {
                'hosts': '@hosts',
                'flow_id': None,
                'reason': '@reason',
                'grr_server_url': 'http://localhost:8000',
                'grr_auth': ('admin', 'admin'),
                'approvers': ['grr-approvals@google.com'],
                'verbose': True,
                'artifact_list': 'AllUsersShellHistory,BrowserHistory,'
                                 'LinuxLogFiles,AllLinuxScheduleFiles,'
                                 'LinuxScheduleFiles,ZeitgeistDatabase,'
                                 'AllShellConfigs',
            },
        }
    ],
    'processors': [
        {
            'name': 'LocalPlasoProcessor',
            'args': {
                'timezone': None,
                'verbose': True,
            },
        }
    ],
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


args = [
    ('hosts', 'Comma-separated list of hosts to process'),
    ('reason', 'Reason for collection'),
]
