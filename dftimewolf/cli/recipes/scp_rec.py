# -*- coding: utf-8 -*-
"""Copy files to a specified destination using scp.
"""

from __future__ import unicode_literals

_short_description = ('Takes a list of file paths and copies them over ssh'
                      'to a specified destination.')

contents = {
    'name':
        'scp',
    'short_description': _short_description,
    'modules': [{
        'wants': [],
        'name': 'Scp',
        'args': {
            'paths': '@paths',
            'destination': '@destination',
            'hostname': '',
            'user': '',
            'id_file': '',
        },
    }]
}

args = [
    ('paths', 'Paths to copy', None),
    ('destination', 'Destination to write the files to', None),
    ('--hostname', 'Destination hostname', ""),
    ('--user', 'Destination user', ""),
    ('--id_file', 'Identity file to use', ""),
]
