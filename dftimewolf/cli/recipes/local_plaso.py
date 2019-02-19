# -*- coding: utf-8 -*-
"""Analyze local file paths with plaso and send results to Timesketch.

- Collectors collect from a path in the FS
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch
"""

from __future__ import unicode_literals

_short_description = ('Processes a list of file paths using plaso and sends '
                      'results to Timesketch.')

contents = {
    'name':
        'local_plaso',
    'short_description': _short_description,
    'modules': [{
        'wants': [],
        'name': 'FilesystemCollector',
        'args': {
            'paths': '@paths',
        },
    }, {
        'wants': ['FilesystemCollector'],
        'name': 'LocalPlasoProcessor',
        'args': {
            'timezone': None,
        },
    }, {
        'wants': ['LocalPlasoProcessor'],
        'name': 'TimesketchExporter',
        'args': {
            'endpoint': '@ts_endpoint',
            'username': '@ts_username',
            'password': '@ts_password',
            'incident_id': '@incident_id',
            'sketch_id': '@sketch_id',
        }
    }]
}

args = [
    ('paths', 'Paths to process', None),
    ('--incident_id', 'Incident ID (used for Timesketch description)', None),
    ('--sketch_id', 'Sketch to which the timeline should be added', None),
]
