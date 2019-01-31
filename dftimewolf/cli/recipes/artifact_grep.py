"""Collect artifacts from hosts using GRR.

- Collect a predefined list of artifacts from hosts using GRR
- Process them locally with grep to extract keywords
"""
from __future__ import unicode_literals

_short_description = ('Fetches requested artifacts from a list of GRR hosts '
                      'and runs grep with a list of provided keywords on them.')

contents = {
    'name':
        'artifact_grep',
    'short_description': _short_description,
    'modules': [{
        'wants': [],
        'name': 'GRRArtifactCollector',
        'args': {
            'hosts': '@hosts',
            'reason': '@reason',
            'grr_server_url': '@grr_server_url',
            'grr_username': '@grr_username',
            'grr_password': '@grr_password',
            'artifacts': '@artifacts',
            'extra_artifacts': '@extra_artifacts',
            'use_tsk': '@use_tsk',
            'approvers': '@approvers',
            'verify': '@verify',
        },
    }, {
        'wants': ['GRRArtifactCollector'],
        'name': 'GrepperSearch',
        'args': {
            'keywords': '@keywords',
        },
    }],
}

args = [
    ('hosts', 'Comma-separated list of hosts to process', None),
    ('reason', 'Reason for collection', None),
    ('--artifacts', 'Comma-separated list of artifacts to fetch '
     '(override default artifacts)', None),
    ('--extra_artifacts', 'Comma-separated list of artifacts to append '
     'to the default artifact list', None),
    ('--use_tsk', 'Use TSK to fetch artifacts', False),
    ('--approvers', 'Emails for GRR approval request', None),
    ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000'),
    ('--verify', 'Whether to verify the GRR TLS certificate', True),
    ('--grr_username', 'GRR username', 'admin'),
    ('--grr_password', 'GRR password', 'admin'),
    ('--keywords', 'Pipe-separated list of keywords to search for '
                   '(e.g. key1|key2|key3', None),
]
