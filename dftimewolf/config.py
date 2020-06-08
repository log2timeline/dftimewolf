# -*- coding: utf-8 -*-
"""Small module to load user configuration parameters."""

import json

from dftimewolf.lib import errors


class Config(object):
  """Class that handles DFTimewolf's configuration parameters."""

  _extra_config = {}

  @classmethod
  def GetExtra(cls, name=None):
    """Retrieves extra configuration parameters.

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
      bool: True if config was successfully loaded, False otherwise.
    """
    try:
      with open(filename, 'rb') as configuration_file:
        json_string = configuration_file.read()
        cls.LoadExtraData(json_string)
        return True
    except (IOError, OSError):
      pass
    return False

  @classmethod
  def LoadExtraData(cls, json_string):
    """Loads extra configuration parameters from a JSON string.

    Args:
      json_string (str): JSON string that contains the configuration.

    Raises:
      BadConfigurationError: if the JSON string cannot be read.
    """
    try:
      json_dict = json.loads(json_string)
    except ValueError as exception:
      raise errors.BadConfigurationError((
          'Unable to read configuration from JSON string with error: '
          '{0!s}').format(exception))

    cls._extra_config.update(json_dict)

  # Note that this method is only used by tests.
  @classmethod
  def ClearExtra(cls):
    """Clears any extra arguments loaded from a config JSON blob."""
    cls._extra_config = {}
