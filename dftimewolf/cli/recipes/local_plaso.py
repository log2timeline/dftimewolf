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
        'name': 'FilesystemCollector',
        'args': {
            'paths': ['@paths'],
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
    'exporters': [{
        'name': 'TimesketchExporter',
        'args': {
            'ts_endpoint': '@ts_endpoint',
            'ts_username': '@ts_username',
            'ts_password': '@ts_password',
            'incident_id': '@incident_id',
            'sketch_id': None,
            'verbose': True,
        }
    }],
}

args = [
    ('paths', 'Paths to process', None),
    ('--incident_id', 'Incident ID (used for Timesketch description)', None),
]
