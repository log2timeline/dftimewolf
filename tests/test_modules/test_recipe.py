# -*- coding: utf-8 -*-
"""Dummy recipe"""

basic_recipe = {
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

basic_no_preflights = {
	'name':
		'dummy_recipe',
	'short_description': 'Nothing to see here.',
	'modules': [{
		'wants': [],
		'name': 'DummyModule1',
		'args': {
			'runtime_value': ''
		},
	}, {
		'wants': ['DummyModule1'],
		'name': 'DummyModule2',
		'args': {},
	}]
}

threaded_no_preflights = {
	'name':
		'dummy_threaded_recipe',
	'short_description': 'Nothing to see here.',
	'modules': [{
		'wants': [],
		'name': 'ContainerGeneratorModule',
		'args': {
			'runtime_value': ''
		},
	}, {
		'wants': ['ContainerGeneratorModule'],
		'name': 'ThreadAwareConsumerModule',
		'args': {},
	}]
}

with_runtime_names = {
	'name':
		'dummy_recipe',
	'short_description': 'Nothing to see here.',
	'preflights': [{
		'name': 'DummyPreflightModule',
		'runtime_name': 'DummyPreflightModule-runtime'
	}],
	'modules': [{
		'wants': [],
		'name': 'DummyModule1',
		'args': {
			'runtime_value': '1-1'
		},
	}, {
		'wants': ['DummyModule1'],
		'name': 'DummyModule2',
		'args': {
			'runtime_value': '2-1'
		},
	}, {
		'wants': ['DummyModule2'],
		'name': 'DummyModule1',
		'runtime_name': 'DummyModule1-2',
		'args': {
			'runtime_value': '1-2'
		},
	}, {
		'wants': ['DummyModule1-2'],
		'name': 'DummyModule2',
		'runtime_name': 'DummyModule2-2',
		'args': {
			'runtime_value': '2-2'
		},
	}]
}

issue_503_recipe = {
	'name': 'issue_503_recipe',
	'short_description': 'Nothing to see here.',
	'modules': [{
		'wants': [],
		'name': 'Issue503Module',
		'args': {},
	}]
}

args = []
