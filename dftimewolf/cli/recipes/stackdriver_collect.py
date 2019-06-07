# -*- coding: utf-8 -*-
"""Collects stackdriver logs from a GCP project."""

from __future__ import unicode_literals

_short_description = (
    'Collects stackdriver logs from a project.')

contents = {
    'name': 'stackdriver_collect',
    'short_description': _short_description,
    'modules': [{
        'wants': [],
        'name': 'StackdriverLogsCollector',
        'args': {
            'project_name': '@project_name',
            'filter_expression': '@filter_expression'
        },
    }]
}

args = [
    ('project_name', 'Name of GCP project to collect logs from', None),
    ('filter_expression', 'Filter expression to use to query Stackdriver logs',
     'resource.type = "gce_instance"')
]
