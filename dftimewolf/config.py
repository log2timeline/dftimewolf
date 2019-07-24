# -*- coding: utf-8 -*-
"""Small module to load user configuration parameters."""

from __future__ import unicode_literals

import json
import sys


class Config(object):
  """Class that handles DFTimewolf's configuration parameters."""

  _module_classes = {}

  _extra_config = {}

  @classmethod
  def GetExtra(cls, name=None):
    """Gets extra configuration parameters.

    These parameters should be loaded through LoadExtra or LoadExtraData.

    Args:
      name (str): name of the configuration data to load.

    Returns:
      dict[str, object]: extra configuration data or None if not configuration
          data is available.
    """
    if not name:
      return cls._extra_config
    return cls._extra_config.get(name, None)

  @classmethod
  def LoadExtra(cls, filename):
    """Loads extra configuration parameters from a JSON configuration file.

    Args:
      filename (str): name of the JSON configuration file.

    Returns:
      bool: True if the extra configuration parameters were read.
    """
    try:
      with open(filename, 'rb') as configuration_file:
        cls.LoadExtraData(configuration_file.read())
        sys.stderr.write("Config successfully loaded from {0:s}\n".format(
            filename))
        return True
    except (IOError, OSError):
      return False

  @classmethod
  def LoadExtraData(cls, data):
    """Loads extra configuration parameters from a JSON data.

    Args:
      data (str): JSON data that contains the configuration.
    """
    try:
      json_dict = json.loads(data)
      cls._extra_config.update(json_dict)

    # TODO: catch JSON errors.
    except ValueError as exception:
      sys.stderr.write('Could convert to JSON. {0:s}'.format(exception))
      # TODO: do not hard exit here but raise BadConfig exception or equiv.
      exit(-1)

  # Not that this methos is only used by tests.
  @classmethod
  def ClearExtra(cls):
    """Clears any extra arguments loaded from a config JSON blob."""
    cls._extra_config = {}
