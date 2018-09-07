"""Fetches specific files from one or more GRR hosts."""
from __future__ import unicode_literals

_short_description = 'Fetches specific files from one or more GRR hosts.'

contents = {
    'name':
        'grr_fetch_files',
    'short_description': _short_description,
    'modules': [{
        'name': 'GRRFileCollector',
        'args': {
            'hosts': '@hosts',
            'reason': '@reason',
            'grr_server_url': '@grr_server_url',
            'grr_username': '@grr_username',
            'grr_password': '@grr_password',
            'files': '@files',
            'use_tsk': '@use_tsk',
            'approvers': '@approvers',
            'verify': '@verify',
        },
    }, {
        'name': 'LocalFilesystemCopy',
        'args': {
            'target_directory': '@directory',
        },
    }],
}

args = [
    ('hosts', 'Comma-separated list of hosts to process', None),
    ('reason', 'Reason for collection', None),
    ('files', 'Comma-separated list of files to fetch (supports GRR variable '
              'interpolation)', None),
    ('directory', 'Directory in which to export files.', None),
    ('--use_tsk', 'Use TSK to fetch artifacts', False),
    ('--approvers', 'Emails for GRR approval request', None),
    ('--verify', 'Whether to verify the GRR TLS certificate', True),
    ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000'),
    ('--grr_username', 'GRR username', 'admin'),
    ('--grr_password', 'GRR password', 'admin'),
]
