#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""dftimewolf main entrypoint."""

from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import signal
import sys

# Make dftimewolf faster by only importing modules if we're not actually
# just asking for help
_ASKING_FOR_HELP = '-h' in sys.argv or '--help' in sys.argv or len(sys.argv) < 2

# pylint: disable=wrong-import-position
from dftimewolf import config

from dftimewolf.lib import errors
from dftimewolf.lib import utils

if not _ASKING_FOR_HELP:
  # Import the collector modules.
  # These will be registered automatically upon import
  # pylint: disable=unused-import
  from dftimewolf.lib import collectors
  from dftimewolf.lib.collectors import filesystem
  from dftimewolf.lib.collectors import gcloud
  from dftimewolf.lib.collectors import grr_hosts
  from dftimewolf.lib.collectors import grr_hunt
  from dftimewolf.lib.collectors import stackdriver
  from dftimewolf.lib.exporters import local_filesystem
  from dftimewolf.lib.exporters import timesketch
  from dftimewolf.lib.processors import grepper
  from dftimewolf.lib.processors import localplaso
  from dftimewolf.lib.processors import turbinia

from dftimewolf.lib.recipes import manager as recipes_manager
from dftimewolf.lib.state import DFTimewolfState


class DFTimewolfTool(object):
  """DFTimewolf tool."""

  _DEFAULT_DATA_FILES_PATH = os.path.join('/', 'usr', 'share', 'dftimewolf')

  def __init__(self):
    """Initializes a DFTimewolf tool."""
    super(DFTimewolfTool, self).__init__()
    self._command_line_options = None
    self._data_files_path = None
    self._recipes_manager = recipes_manager.RecipesManager()
    self._recipe = None
    self._state = None

    self._DetermineDataFilesPath()

  def _AddRecipeOptions(self, argument_parser):
    """Adds the recipe options to the argument group.

    Args:
      argument_parser (argparse.ArgumentParser): argparse argument parser.
    """
    subparsers = argument_parser.add_subparsers()

    for recipe in self._recipes_manager.GetRecipes():
      description = '\n'.join(recipe.description)
      subparser = subparsers.add_parser(
          recipe.name, formatter_class=utils.DFTimewolfFormatterClass,
          description=description)
      subparser.set_defaults(recipe=recipe.contents)

      for switch, help_text, default in recipe.args:
        subparser.add_argument(switch, help=help_text, default=default)

      # Override recipe defaults with those specified in Config
      # so that they can in turn be overridden in the commandline
      subparser.set_defaults(**config.Config.get_extra())

  def _DetermineDataFilesPath(self):
    """Determines the data files path."""
    data_files_path = os.path.realpath(__file__)
    data_files_path = os.path.dirname(data_files_path)
    data_files_path = os.path.dirname(data_files_path)
    data_files_path = os.path.dirname(data_files_path)
    data_files_path = os.path.join(data_files_path, 'data')

    if not os.path.isdir(data_files_path):
      data_files_path = self._DEFAULT_DATA_FILES_PATH

    self._data_files_path = data_files_path

  def _GenerateHelpText(self):
    """Generates help text with alphabetically sorted recipes.

    Returns:
      str: help text.
    """
    recipes = self._recipes_manager.GetRecipes()
    if not recipes:
      help_text = '\nNo recipes found.'
    else:
      help_text = '\nAvailable recipes:\n\n'
      for recipe in recipes:
        short_description = recipe.contents.get(
            'short_description', 'No description')
        help_text += ' {0:<35s}{1:s}\n'.format(recipe.name, short_description)

    return help_text

  def LoadConfiguration(self):
    """Loads the configuration."""
    configuration_file_path = os.path.join(self._data_files_path, 'config.json')
    # Try to open config.json and load configuration data from it.
    config.Config.load_extra(configuration_file_path)

    user_directory = os.path.expanduser('~')
    configuration_file_path = os.path.join(user_directory, '.dftimewolfrc')
    config.Config.load_extra(configuration_file_path)

    configuration_file_path = os.path.join('/', 'etc', 'dftimewolf.conf')
    config.Config.load_extra(configuration_file_path)

    configuration_file_path = os.path.join(
        '/', 'usr', 'share', 'dftimewolf', 'dftimewolf.conf')
    config.Config.load_extra(configuration_file_path)

  def ParseArguments(self, arguments):
    """Parses the command line arguments.

    Args:
      arguments (list[str]): command line arguments.

    Returns:
      bool: True if the arguments were successfully parsed.
    """
    help_text = self._GenerateHelpText()

    argument_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=help_text)

    self._AddRecipeOptions(argument_parser)

    self._command_line_options = argument_parser.parse_args(arguments)
    self._recipe = self._command_line_options.recipe

    self._state = DFTimewolfState(config.Config)
    print('Loading recipe...')
    self._state.load_recipe(self._recipe)

    number_of_modules = len(self._recipe['modules'])
    print('Loaded recipe {0:s} with {1:d} modules'.format(
        self._recipe['name'], number_of_modules))

    return True

  def ReadRecipes(self):
    """Reads the recipe files."""
    if os.path.isdir(self._data_files_path):
      recipes_path = os.path.join(self._data_files_path, 'recipes')
      if os.path.isdir(recipes_path):
        self._recipes_manager.ReadRecipesFromDirectory(recipes_path)

  def RunModules(self):
    """Runs the modules."""
    print('Running modules...')
    self._state.run_modules()
    print('Recipe {0:s} executed successfully.'.format(self._recipe['name']))

  def SetupModules(self):
    """Sets up the modules."""
    # TODO: refactor to only load modules that are used by the recipe.

    print('Setting up modules...')
    self._state.setup_modules(self._command_line_options)
    print('Modules successfully set up!')


def Main():
  """Main function for DFTimewolf.

  Returns:
    bool: True if DFTimewolf could be run successfully, False otherwise.
  """
  version_tuple = (sys.version_info[0], sys.version_info[1])
  if version_tuple[0] != 3 or version_tuple < (3, 6):
    print(('Unsupported Python version: {0:s}, version 3.6 or higher '
           'required.').format(sys.version))
    return False

  tool = DFTimewolfTool()

  # TODO: print errors if this fails.
  tool.LoadConfiguration()

  try:
    tool.ReadRecipes()
  except (KeyError, errors.RecipeParseError) as exception:
    print('{0!s}'.format(exception))
    return False

  if not tool.ParseArguments(sys.argv[1:]):
    # TODO: print errors if this fails.
    return False

  # TODO: print errors if this fails.
  tool.SetupModules()

  # TODO: print errors if this fails.
  tool.RunModules()

  return True


if __name__ == '__main__':
  signal.signal(signal.SIGINT, utils.signal_handler)
  if Main():
    sys.exit(0)
  else:
    sys.exit(1)
