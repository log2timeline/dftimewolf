"""DFTimewolf recipe for starting file hunts using GRR.

Consists of a single collector that starts the hunt and provides a Hunt ID to
the user.
"""

__author__ = u'tomchop@google.com (Thomas Chopitea)'

contents = {
    'name':
        'grr_hunt_file',
    'params': {},
    'collectors': [{
        'name': 'GRRHuntFileCollector',
        'args': {
            'file_list': '@file_list',
            'reason': '@reason',
            'grr_server_url': 'http://localhost:8000',
            'grr_auth': ('admin', 'admin'),
            'approvers': ['grr-approvals@google.com'],
            'verbose': True,
        },
    }],
    'processors': [],
    'exporters': [],
}

args = [
    ('file_list', 'Comma-separated list of filepaths to hunt for', None),
    ('reason', 'Reason for collection', None),
]
