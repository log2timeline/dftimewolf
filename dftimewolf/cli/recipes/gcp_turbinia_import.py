# -*- coding: utf-8 -*-
"""Imports a remote GCP persistent disk and sends to Turbinia and Timesketch.

This copies a disk from a remote GCP project and sends to Turbinia for
processing and then sends those results to Timesketch. It will also start an
analysis VM with the attached disk. If you want to process a disk already in
the same project as Turbinia you can use the gcp_turbinia recipe.
"""

from __future__ import unicode_literals
from datetime import datetime

_short_description = ('Imports a remote GCP persistent disk, processes it with '
                      'Turbinia and sends results to Timesketch.')

contents = {
    'name': 'gcp_turbinia_import',
    'short_description': _short_description,
    'modules': [{
        'name': 'GoogleCloudCollector',
        'args': {
            'analysis_project_name': '@analysis_project_name',
            'remote_project_name': '@remote_project_name',
            'remote_instance_name': '@instance',
            'incident_id': '@incident_id',
            'zone': '@zone',
            'disk_names': '@disks',
            'all_disks': '@all_disks',
            'boot_disk_size': '@boot_disk_size',
        },
    }, {
        'name': 'TurbiniaProcessor',
        'args': {
            'disk_name': None,  # Taken from GoogleCloudCollector's output
            'project': '@analysis_project_name',
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
    ('remote_project_name',
     'Name of the project containing the instance / disks to copy ', None),
    ('--zone', 'The GCP zone the disk to process (and Turbinia workers) are in',
     None),
    ('--incident_id', 'Incident ID (used for Timesketch description)',
     datetime.now().strftime("%Y%m%d%H%M%S")),
    ('--sketch_id', 'Sketch to which the timeline should be added', None),
    ('--timesketch_endpoint', 'Endpoint of the Timesketch server to use',
     'https://localhost:5000'),
    ('--instance', 'Name of the instance to analyze.', None),
    ('--disks', 'Comma-separated list of disks to copy.', None),
    ('--all_disks', 'Copy all disks in the designated instance. '
                    'Overrides disk_names if specified', False),
    ('--analysis_project_name', 'Name of the project where the analysis VM will'
                                ' be created', None),
    ('--boot_disk_size', 'The size of the analysis VM boot disk (in GB)', 50.0),
]
