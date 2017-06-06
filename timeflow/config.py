"""Small module to search for and load configuration files."""

import json
import os

LOCATIONS = [
    os.curdir,
    os.path.expanduser('~'),
    os.environ.get('TIMEFLOW_CONFIG'),
]

FILENAMES = [
    'timeflow.json',
    '.timeflowrc',
]

_CONFIG = None


def get_config():
  """Searches several locations for a timeflow_config.json file.

  Searches for a timeflow_config.json file in the current directory, user's home
  directory, or an TIMEFLOW_CONFIG environment variable. If found file is
  decoded as a JSON object.

  Returns:
    JSON object or None
  """
  # pylint: disable=W0603
  global _CONFIG
  if not _CONFIG:
    for location in LOCATIONS:
      for filename in FILENAMES:
        if location and filename:
          try:
            full_path = os.path.abspath(os.path.join(location, filename))
            with open(full_path) as config:
              _CONFIG = json.loads(config.read())
              return _CONFIG
          except IOError:
            pass
    print 'WARNNING: No .timeflowrc file found. See README for details'
    exit(-1)
  else:
    return _CONFIG
