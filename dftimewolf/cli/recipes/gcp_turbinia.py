# -*- coding: utf-8 -*-
"""Process a GCP persistent disk with Turbinia and send output to Timesketch.

This processes a disk that is already in the project where Turbinia exists. If
you want to copy the disk from another project, use the gcp_turbinia_import
recipe.
"""

from __future__ import unicode_literals

_short_description = (
    'Processes a GCP persistent disk already in our forensics analysis project '
    'with Turbinia and sends the results to Timesketch.')

contents = {
    'name': 'gcp_turbinia',
    'short_description': _short_description,
    'modules': [{
        'wants': [],
        'name': 'TurbiniaProcessor',
        'args': {
            'disk_name': '@disk_name',
            'project': '@analysis_project_name',
            'turbinia_zone': '@turbinia_zone',
        },
    }, {
        'wants': ['TurbiniaProcessor'],
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
    ('analysis_project_name', 'Name of GCP project the disk exists in', None),
    ('turbinia_zone',
     'The GCP zone the disk to process (and Turbinia workers) are in', None),
    ('disk_name', 'Name of GCP persistent disk to process', None),
    ('--incident_id', 'Incident ID (used for Timesketch description)', None),
    ('--sketch_id', 'Sketch to which the timeline should be added', None),
]
