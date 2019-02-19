"""Upload a CSV file or Plaso file to Timesketch."""

from __future__ import unicode_literals

_short_description = 'Uploads a .plaso file to Timesketch.'

contents = {
    'name': 'timesketch_upload',
    'short_description': _short_description,
    'modules': [{
        'wants': [],
        'name': 'FilesystemCollector',
        'args': {
            'paths': '@files',
        },
    }, {
        'wants': ['FilesystemCollector'],
        'name': 'TimesketchExporter',
        'args': {
            'endpoint': '@ts_endpoint',
            'username': '@ts_username',
            'password': '@ts_password',
            'incident_id': '@incident_id',
            'sketch_id': '@sketch_id',
        }
    }],
}

args = [
    ('files', 'Comma-separated list of paths to CSV files or Plaso storage'
              ' files', None),
    ('--sketch_id', 'Sketch to which the timeline should be added', None),
    ('--incident_id', 'Incident ID (used for Timesketch description)', None)
]
