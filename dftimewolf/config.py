# -*- coding: utf-8 -*-
"""Small module to load user configuration parameters."""

from __future__ import unicode_literals

import json
import sys

from dftimewolf.lib.modules import manager as modules_manager


class Config(object):
  """Class that handles DFTimewolf's configuration parameters."""

  _module_classes = {}

  _extra_config = {}

  @classmethod
  def get_extra(cls, name=None):
    """Gets extra configuration parameters.

    These parameters should be loaded through load_extra or load_extra_data.

    Args:
      name: str, the name of the configuration data to load.

    Returns:
      A dictionary containing the requested configuration data. None if
      data was never loaded under that name.
    """
    if not name:
      return cls._extra_config
    return cls._extra_config.get(name, None)

  @classmethod
  def has_extra(cls, name):
    """Checks if an named configuration parameter has been provided.

    Args:
      name: str, the name of the configuration data to load.

    Returns:
      True if parameter is provided in the extra configuration data, false
      otherwise.
    """
    return name in cls._extra_config

  @classmethod
  def load_extra(cls, filename):
    """Loads extra JSON configuration parameters from a file on the filesystem.

    Args:
      filename: str, the filename to open.

    Returns:
      bool: True if the extra configuration parameters were read.
    """
    try:
      with open(filename, 'rb') as configuration_file:
        cls.load_extra_data(configuration_file.read())
        sys.stderr.write("Config successfully loaded from {0:s}\n".format(
            filename))
        return True
    except IOError:
      return False

  @classmethod
  def load_extra_data(cls, data):
    """Loads extra JSON configuration parameters from a data buffer.

    The data buffer must represent a JSON object.

    Args:
      data: str, the buffer to load the JSON data from.
    """
    try:
      cls._extra_config.update(json.loads(data))
    except ValueError as exception:
      sys.stderr.write('Could convert to JSON. {0:s}'.format(exception))
      exit(-1)

  @classmethod
  def clear_extra(cls):
    """Clears any extra arguments loaded from a config JSON blob."""
    cls._extra_config = {}

  @classmethod
  def register_module(cls, module_class):
    """Registers a dftimewolf collector.

    Args:
      module_class [type]: the module class, which is a subclass of BaseModule.
    """
    modules_manager.ModulesManager.RegisterModule(module_class)

  @classmethod
  def get_module(cls, name):
    """Fetches a previously registered module.

    Args:
      name [str]: name with which the module was registered.

    Returns:
      type: the module class, which is a subclass of BaseModule, or None if
          no corresponding module was found.
    """
    return modules_manager.ModulesManager.GetModuleByName(name)
