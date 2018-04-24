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
        'name': 'GRRFlowCollector',
        'args': {
            'host': '@host',
            'flow_id': '@flow_id',
            'reason': '@reason',
            'grr_server_url': '@grr_server_url',
            'grr_auth': ('admin', 'admin'),
            'approvers': '@approvers',
        },
    }, {
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
    ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000')
]
