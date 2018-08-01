# -*- coding: utf-8 -*-
"""Process a GCP persistent disk with Turbinia and send output to Timesketch.

This processes a disk that is already in the project where Turbinia exists. If
you want to copy the disk from another project, use the gcp_turbinia_import
recipe.
"""

from __future__ import unicode_literals

_short_description = ('Processes a GCP persistent disk with Turbinia and sends '
                      'results to Timesketch.')

contents = {
    'name': 'gcp_turbinia',
    'short_description': _short_description,
    'modules': [{
        'name': 'TurbiniaProcessor',
        'args': {
            'disk_name': '@disk_name',
            'project': '@project',
            'zone': '@zone',
        },
    }, {
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
    ('disk_name', 'Name of GCP persistent disk to process', None),
    ('project', 'Name of GCP project disk exists in', None),
    ('zone', 'The GCP zone the disk to process (and Turbinia workers) are in',
     None),
    ('--incident_id', 'Incident ID (used for Timesketch description)', None),
    ('--sketch_id', 'Sketch to which the timeline should be added', None),
]
