# -*- coding: utf-8 -*-
"""DFTimewolf recipe for collecting data from the filesystem.

- Collectors collect from a path in the FS
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch
"""

__author__ = 'tomchop@google.com (Thomas Chopitea)'

contents = {
    'name': 'grr_huntresults_plaso_timesketch',
    'params': {},
    'collectors': [{
        'name': 'GRRHuntDownloader',
        'args': {
            'hunt_id': '@hunt_id',
            'grr_server_url': 'http://localhost:8000',
            'grr_auth': ('admin', 'admin'),
            'verbose': True,
            'reason': '@reason',
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
    ('hunt_id', 'ID of GRR Hunt results to fetch'),
    ('reason', 'Reason for exporting hunt (used for Timesketch description)'),
]
