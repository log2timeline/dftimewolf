"""DFTimewolf recipe for starting file hunts using GRR.

Consists of a single collector that starts the hunt and provides a Hunt ID to
the user. Feed the Hunt ID to grr_huntresults_plaso_timesketch to process them
through plaso and send them to Timesketch.
"""
from __future__ import unicode_literals

contents = {
    'name':
        'grr_hunt_file',
    'params': {},
    'collectors': [{
        'name': 'GRRHuntFileCollector',
        'args': {
            'file_list': '@file_list',
            'reason': '@reason',
            'grr_server_url': '@grr_server_url',
            'grr_auth': ('admin', 'admin'),
            'approvers': "",
            'verbose': True,
        },
    }],
    'processors': [],
    'exporters': [],
}

args = [
    ('file_list', 'Comma-separated list of filepaths to hunt for', None),
    ('reason', 'Reason for collection', None),
    ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000')
]
