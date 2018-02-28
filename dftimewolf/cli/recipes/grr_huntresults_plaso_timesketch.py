# -*- coding: utf-8 -*-
"""Download the results of a GRR hunt and process them.

- Collect results of a hunt given its Hunt ID
- Processes results with a local install of plaso
- Exports processed items to a new Timesketch sketch
"""
from __future__ import unicode_literals

_short_description = ('Fetches the findings of a GRR hunt, processes them with '
                      'plaso, and sends the results to Timesketch.')

contents = {
    'name':
        'grr_huntresults_plaso_timesketch',
    'short_description': _short_description,
    'collectors': [{
        'name': 'GRRHuntDownloader',
        'args': {
            'hunt_id': '@hunt_id',
            'grr_server_url': '@grr_server_url',
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
            'sketch_id': '@sketch_id',
            'verbose': True,
        }
    }],
}

args = [
    ('hunt_id', 'ID of GRR Hunt results to fetch', None),
    ('reason', 'Reason for exporting hunt (used for Timesketch description)',
     None),
    ('--sketch_id', 'Sketch to which the timeline should be added', None),
    ('--grr_server_url', 'GRR endpoint', 'http://localhost:8000')
]
