"""Collect artifacts from hosts using GRR.

- Collect a predefined list of artifacts from hosts using GRR
- Process them with a local install of plaso
- Export them to a Timesketch sketch
"""
from __future__ import unicode_literals

_short_description = ('Fetches default artifacts from a list of GRR hosts, '
                      'processes them with plaso, and sends the results to '
                      'Timesketch.')

contents = {
    'name':
        'grr_artifact_hosts',
    'short_description': _short_description,
    'collectors': [{
        'name': 'GRRArtifactCollector',
        'args': {
            'hosts': '@hosts',
            'flow_id': None,
            'reason': '@reason',
            'grr_server_url': '@grr_server_url',
            'grr_auth': ('admin', 'admin'),
            'approvers': '',
            'verbose': True,
            'artifact_list': '@artifact_list',
            'extra_artifacts': '@extra_artifacts',
            'use_tsk': '@use_tsk',
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
    ('--use_tsk', 'Use TSK to fetch artifacts', False),
    ('--sketch_id', 'Sketch to which the timeline should be added', None),
    ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000')
]
