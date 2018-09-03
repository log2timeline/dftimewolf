"""Start a GRR file hunt.

Consists of a single collector that starts the hunt and provides a Hunt ID to
the user. Feed the Hunt ID to grr_huntresults_plaso_timesketch to process them
through plaso and send them to Timesketch.
"""
from __future__ import unicode_literals

_short_description = 'Starts a GRR hunt for a list of files.'

contents = {
    'name':
        'grr_hunt_file',
    'short_description': _short_description,
    'modules': [{
        'name': 'GRRHuntFileCollector',
        'args': {
            'file_path_list': '@file_path_list',
            'reason': '@reason',
            'grr_server_url': '@grr_server_url',
            'grr_auth': ('admin', 'admin'),
            'approvers': '@approvers',
            'verify': '@verify',
        },
    }],
    'processors': [],
    'exporters': [],
}

args = [
    ('file_path_list', 'Comma-separated list of file paths to hunt for', None),
    ('reason', 'Reason for collection', None),
    ('--approvers', 'Emails for GRR approval request', None),
    ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000'),
    ('--verify', 'Whether to verify the GRR TLS certificate', True),
]
