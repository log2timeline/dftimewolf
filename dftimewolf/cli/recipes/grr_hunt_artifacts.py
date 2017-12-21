"""DFTimewolf recipe for starting artifact hunts using GRR.

Consists of a single collector that starts the hunt and provides a Hunt ID to
the user. Feed the Hunt ID to grr_huntresults_plaso_timesketch to process them
through plaso and send them to Timesketch.
"""
from __future__ import unicode_literals

contents = {
    'name':
        'grr_hunt_artifacts',
    'params': {},
    'collectors': [{
        'name': 'GRRHuntArtifactCollector',
        'args': {
            'artifacts': '@artifacts',
            'reason': '@reason',
            'grr_server_url': 'http://localhost:8000',
            'grr_auth': ('admin', 'admin'),
            'use_tsk': "@use_tsk",
            'approvers': "",
            'verbose': True,
        },
    }],
    'processors': [],
    'exporters': [],
}

args = [
    ('artifacts', 'Comma-separated list of artifacts to hunt for', None),
    ('reason', 'Reason for collection', None),
    ('use_tsk', 'Use TSK to fetch artifacts', False),
]
