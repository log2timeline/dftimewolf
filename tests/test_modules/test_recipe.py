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

named_modules_contents = {
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
    }, {
        'wants': ['DummyModule2'],
        'name': 'DummyModule1',
        'runtime_name': 'DummyModule1-2',
        'args': {},
    }, {
        'wants': ['DummyModule1-2'],
        'name': 'DummyModule2',
        'runtime_name': 'DummyModule2-2',
        'args': {},
    }]
}

args = []
