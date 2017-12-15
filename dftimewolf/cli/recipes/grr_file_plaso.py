# -*- coding: utf-8 -*-
"""DFTimewolf recipe for collecting data from the filesystem.

- Collectors collect from a path in the FS
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch
"""

from __future__ import unicode_literals

name = 'local_plaso'

contents = {
    'name':
        'local_plaso',
    'params': {},
    'collectors': [{
        'name': 'GRRFileCollector',
        'args': {
          'artifacts': '@artifacts',
          'reason': '@reason',
          'grr_server_url': 'http://localhost:8000',
          'grr_auth': ('admin', 'demo'),
          'use_tsk': False,
          'files': ['@paths'],
          'verbose': True,
        },
    }],
    'processors': [{
        'name': 'LocalPlasoProcessor',
        'args': {
            'timezone': None,
            'verbose': True,
        },
    }],
}

args = [
    ('paths', 'Paths to files to collect', None),
]
