"""DFTimewolf recipe for starting artifact hunts using GRR.

Consists of a single collector that starts the hunt and provides a Hunt ID to
the user.
"""

from __future__ import unicode_literals

contents = {
    'name':
        'grr_flow_download',
    'params': {},
    'collectors': [{
        'name': 'GRRFlowCollector',
        'args': {
            'hosts': '@host',
            'flow_ids': '@flow_id',
            'reason': '@reason',
            'grr_server_url': 'http://localhost:8000',
            'grr_auth': ('admin', 'admin'),
            'use_tsk': False,
            'approvers': [],
            'verbose': True,
        },
    }],
    'processors': [],
    'exporters': [{
        'name': 'LocalFilesystemExporter',
        'args': {
            'directory': '@directory',
        },
    }],
}

args = [
    ('host', 'Hostname to collect the flow from', None),
    ('flow_ids', 'Comma-separated list of flow IDs to download', None),
    ('reason', 'Reason for collection', None),
    ('directory', 'Directory in which to export files.', None),
]
