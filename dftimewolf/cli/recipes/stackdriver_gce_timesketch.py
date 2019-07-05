# -*- coding: utf-8 -*-
"""Loads GCE Cloud Audit logs into Timesketch."""

from __future__ import unicode_literals

_short_description = (
    'Loads GCP Cloud Audit Logs for GCE into Timesketch.')

contents = {
    'name':
        'stackdriver_gce_timesketch',
    'short_description':
        _short_description,
    'modules': [{
        'wants': [],
        'name': 'StackdriverLogsCollector',
        'args': {
            'project_name': '@project_name',
            'filter_expression':
                'logName=projects/@project_name/logs/'
                'cloudaudit.googleapis.com%2Factivity '
                'resource.type:"gce" '
                'timestamp>"@start_date" timestamp<"@end_date"'
        }
    }, {
        'wants': ['StackdriverLogsCollector'],
        'name': 'StackdriverTimesketch',
        'args': {}
    }, {
        'wants': ['StackdriverTimesketch'],
        'name': 'TimesketchExporter',
        'args': {
            'endpoint': '@ts_endpoint',
            'username': '@ts_username',
            'password': '@ts_password',
            'incident_id': '@reason',
            'sketch_id': '@sketch_id',
        }
    }]
}

args = [
    ('project_name', 'Name of GCP project to collect logs from', None),
    ('start_date', 'Start date (yyyy-mm-ddTHH:MM:SSZ)', None),
    ('end_date', 'End date (yyyy-mm-ddTHH:MM:SSZ)', None),
]
