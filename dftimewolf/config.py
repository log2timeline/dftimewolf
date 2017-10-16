# -*- coding: utf-8 -*-
"""Small module to load user configuration parameters."""

from __future__ import unicode_literals

import json
import sys

from dftimewolf.lib import utils as dftw_utils


class Config(object):
  """Class that handles DFTimewolf's configuration parameters."""

  _recipe_classes = {}
  _collector_classes = {}
  _processor_classes = {}
  _exporter_classes = {}

  _extra_config = {}

  @classmethod
  def get_extra(cls, name):
    """Gets extra configuration parameters.

    These parameters should be loaded through load_extra or load_extra_data.

    Args:
      name: str, the name of the configuration data to load.

    Returns:
      A dictionary containing the requested configuration data. None if
      data was never loaded under that name.
    """
    return cls._extra_config.get(name, None)

  @classmethod
  def load_extra(cls, filename):
    """Loads extra JSON configuration parameters from a file on the filesystem.

    Args:
      filename: str, the filename to open.
    """
    with open(filename, 'rb') as fp:
      try:
        cls.load_extra_data(fp.read())
      except IOError as e:
        sys.stderr.write('Could not open {0:s}. {1:s}'.format(filename, e))
        exit(-1)

  @classmethod
  def load_extra_data(cls, data):
    """Loads extra JSON configuration parameters from a data buffer.

    The data buffer must represent a JSON object.

    Args:
      data: str, the buffer to load the JSON data from.
    """
    try:
      cls._extra_config.update(json.loads(data))
    except ValueError as e:
      sys.stderr.write('Could convert to JSON. {0:s}'.format(e))
      exit(-1)

  @classmethod
  def clear_extra(cls):
    """Clears any extra arguments loaded from a config JSON blob."""
    cls._extra_config = {}

  @classmethod
  def register_recipe(cls, recipe, **kwargs):
    """Registers a dftimewolf recipe.

    Registers a DFTimeWolf recipe with specified parameters. Parameters can be
    specified in three ways, in order of precedence:
      * Defined in config.json
      * Passed as arguments to the register_recipe function call
      * Passed as CLI args

    Args:
      recipe: imported python module representing the recipe.
      **kwargs: parameters to be replaced in the recipe before checking the
          CLI arguments.
    """
    # Update kwargs with what we already loaded from config.json
    recipe_name = recipe.contents['name']
    cls._recipe_classes[recipe_name] = (recipe.contents, recipe.args)

  @classmethod
  def get_registered_recipes(cls):
    """Fetches all registered recipes.

    Returns:
      List of registered (recipe, args) tuples.
    """
    return cls._recipe_classes.values()

  @classmethod
  def register_collector(cls, collector_class):
    """Registers a dftimewolf collector.

    Args:
      collector_class: Python class extending BaseCollector.
    """
    cls._collector_classes[collector_class.__name__] = collector_class

  @classmethod
  def get_collector(cls, name):
    """Fetches a previously registered collector.

    Args:
      name: str, name with which the collector was registered.

    Returns:
      Corresponding class extending BaseCollector.
    """
    return cls._collector_classes[name]

  @classmethod
  def register_processor(cls, processor_class):
    """Registers a dftimewolf processor.

    Args:
      processor_class: Python class extending BaseProcessor.
    """
    cls._processor_classes[processor_class.__name__] = processor_class

  @classmethod
  def get_processor(cls, name):
    """Fetches a previously registered processor.

    Args:
      name: str, name with which the processor was registered.

    Returns:
      Corresponding class extending BaseProcessor.
    """
    return cls._processor_classes[name]

  @classmethod
  def register_exporter(cls, exporter_class):
    """Registers a dftimewolf exporter.

    Args:
      exporter_class: Python class extending BaseExporter.
    """
    cls._exporter_classes[exporter_class.__name__] = exporter_class

  @classmethod
  def get_exporter(cls, name):
    """Fetches a previously registered exporter.

    Args:
      name: str, name with which the exporter was registered.

    Returns:
      Corresponding class extending BaseExporter.
    """
    return cls._exporter_classes[name]
