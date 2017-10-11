"""DFTimewolf recipe for starting artifact hunts using GRR.

Consists of a single collector that starts the hunt and provides a Hunt ID to
the user.
"""

__author__ = u'tomchop@google.com (Thomas Chopitea)'

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
            'use_tsk': False,
            'approvers': ['grr-approvals@google.com'],
            'verbose': True,
        },
    }],
    'processors': [],
    'exporters': [],
}

args = [
    ('artifacts', 'Comma-separated list of artifacts to hunt for'),
    ('reason', 'Reason for collection'),
]
