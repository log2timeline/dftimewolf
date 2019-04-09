# -*- coding: utf-8 -*-
"""Dummy recipe"""

from __future__ import unicode_literals

contents = {
    'name':
        'dummy_recipe',
    'short_description': 'Nothing to see here.',
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
