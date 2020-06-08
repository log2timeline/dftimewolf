# -*- coding: utf-8 -*-
"""Dummy recipe"""

contents = {
    'name':
        'dummy_recipe',
    'short_description': 'Nothing to see here.',
    'preflights': [{
        'name': 'DummyPreflightModule'
    }],
    'modules': [{
        'wants': [],
        'name': 'DummyModule1',
        'args': {},
    }, {
        'wants': ['DummyModule1'],
        'name': 'DummyModule2',
        'args': {},
    }]
}

args = []
