"""Download GRR flows.

Consists of a single collector that downloads data collected by a GRR flow and
saves it to the local filesystem.
"""
from __future__ import unicode_literals

_short_description = ('Downloads the contents of a specific GRR flow to '
                      'the filesystem.')

contents = {
    'name':
        'grr_flow_download',
    'short_description': _short_description,
    'modules': [{
        'wants': [],
        'name': 'GRRFlowCollector',
        'args': {
            'host': '@host',
            'flow_id': '@flow_id',
            'reason': '@reason',
            'grr_server_url': '@grr_server_url',
            'grr_username': '@grr_username',
            'grr_password': '@grr_password',
            'approvers': '@approvers',
            'verify': '@verify',
        },
    }, {
        'wants': ['GRRFlowCollector'],
        'name': 'LocalFilesystemCopy',
        'args': {
            'target_directory': '@directory',
        },
    }],
}

args = [
    ('host', 'Hostname to collect the flow from', None),
    ('flow_id', 'Flow ID to download', None),
    ('reason', 'Reason for collection', None),
    ('directory', 'Directory in which to export files.', None),
    ('--approvers', 'Emails for GRR approval request', None),
    ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000'),
    ('--verify', 'Whether to verify the GRR TLS certificate', True),
    ('--grr_username', 'GRR username', 'admin'),
    ('--grr_password', 'GRR password', 'admin'),
]
