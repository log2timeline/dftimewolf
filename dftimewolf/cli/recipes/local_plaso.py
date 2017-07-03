"""DFTimewolf recipe for collecting data from the filesystem.

- Collectors collect from a path in the FS
- Processes them with a local install of plaso
- Exports them to a new Timesketch sketch
"""

__author__ = u'tomchop@google.com (Thomas Chopitea)'
from dftimewolf.internals import get_config

RECIPE = {
    'name': 'local_plaso',
    'params': {},
    'collectors': [
        {
            'name': 'filesystem',
            'args': {
                'paths': ['@paths'],
                'verbose': True,
            },
        }
    ],
    'processors': [
        {
            'name': 'localplaso',
            'args': {
                'timezone': None,
                'verbose': True,
            },
        }
    ],
    'exporters': [
        {
            'name': 'timesketch',
            'args': {
                'ts_endpoint': get_config()['timesketch']['endpoint'],
                'ts_username': get_config()['timesketch']['username'],
                'ts_password': get_config()['timesketch']['password'],
                'incident_id': '@incident_id',
                'sketch_id': None,
                'verbose': True,
            }
        }
    ],
}

ARGS = [
    ('paths', 'Paths to process'),
    ('--incident_id', 'Incident ID (used for Timesketch descrption)'),
]
