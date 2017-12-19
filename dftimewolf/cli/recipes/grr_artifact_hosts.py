"""DFTimewolf recipe for collecting artifacts from hosts using GRR.

- Collectors collect a predefined list of artifacts from hosts using GRR
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
            'approvers': "",
            'verbose': True,
            'artifact_list': '@artifact_list',
            'extra_artifacts': '@extra_artifacts',
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
            'sketch_id': '@sketch_id',
            'verbose': True,
        }
    }],
}

args = [
    ('hosts', 'Comma-separated list of hosts to process', None),
    ('reason', 'Reason for collection', None),
    ('--artifact_list', 'Comma-separated list of artifacts to fetch '
     '(override default artifacts)', None),
    ('--extra_artifacts', 'Comma-separated list of artifacts to append '
     'to the default artifact list', None),
    ('--sketch_id', 'Sketch to which the timeline should be added', None)
]
