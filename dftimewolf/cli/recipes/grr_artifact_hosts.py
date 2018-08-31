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
    'modules': [{
        'name': 'GRRArtifactCollector',
        'args': {
            'hosts': '@hosts',
            'reason': '@reason',
            'grr_server_url': '@grr_server_url',
            'grr_auth': ('admin', 'admin'),
            'artifacts': '@artifacts',
            'extra_artifacts': '@extra_artifacts',
            'use_tsk': '@use_tsk',
            'approvers': '@approvers',
            'verify': True,
        },
    }, {
        'name': 'LocalPlasoProcessor',
        'args': {
            'timezone': None,
        },
    }, {
        'name': 'TimesketchExporter',
        'args': {
            'endpoint': '@ts_endpoint',
            'username': '@ts_username',
            'password': '@ts_password',
            'incident_id': '@reason',
            'sketch_id': '@sketch_id',
        }
    }],
}

args = [
    ('hosts', 'Comma-separated list of hosts to process', None),
    ('reason', 'Reason for collection', None),
    ('--artifacts', 'Comma-separated list of artifacts to fetch '
     '(override default artifacts)', None),
    ('--extra_artifacts', 'Comma-separated list of artifacts to append '
     'to the default artifact list', None),
    ('--use_tsk', 'Use TSK to fetch artifacts', False),
    ('--approvers', 'Emails for GRR approval request', None),
    ('--sketch_id', 'Sketch to which the timeline should be added', None),
    ('--incident_id', 'Incident ID (used for Timesketch description)', None),
    ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000')
]
