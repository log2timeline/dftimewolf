"""Start a GRR artifact hunt.

Consists of a single collector that starts the hunt and provides a Hunt ID to
the user. Feed the Hunt ID to grr_huntresults_plaso_timesketch to process them
through plaso and send them to Timesketch.
"""
from __future__ import unicode_literals

_short_description = 'Starts a GRR hunt for the default set of artifacts.'

contents = {
    'name':
        'grr_hunt_artifacts',
    'short_description': _short_description,
    'modules': [{
        'name': 'GRRHuntArtifactCollector',
        'args': {
            'artifacts': '@artifacts',
            'reason': '@reason',
            'grr_server_url': '@grr_server_url',
            'grr_auth': ('admin', 'admin'),
            'use_tsk': "@use_tsk",
            'approvers': '@approvers',
            'verify': True,
        },
    }],
}

args = [
    ('artifacts', 'Comma-separated list of artifacts to hunt for', None),
    ('reason', 'Reason for collection', None),
    ('--use_tsk', 'Use TSK to fetch artifacts', False),
    ('--approvers', 'Emails for GRR approval request', None),
    ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000')
]
