"""Timeflow recipe for collecting data from hosts using GRR.

- Collectors collect default artifacts from hosts using GRR
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch

"""

__author__ = u'tomchop@google.com (Thomas Chopitea)'


contents = {
    'name': 'grr_hunt_file',
    'params': {},
    'collectors': [
        {
            'name': 'GRRHuntFileCollector',
            'args': {
                'file_list': '@file_list',
                'reason': '@reason',
                'grr_server_url': 'http://localhost:8000',
                'grr_auth': ('admin', 'admin'),
                'approvers': ['grr-approvals@google.com'],
                'verbose': True,
            },
        }
    ],
    'processors': [],
    'exporters': [],
}

args = [
    ('file_list', 'Comma-separated list of filepaths to hunt for'),
    ('reason', 'Reason for collection'),
]
