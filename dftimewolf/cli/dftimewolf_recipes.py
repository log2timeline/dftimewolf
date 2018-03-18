# -*- coding: utf-8 -*-
"""dftimewolf main entrypoint."""

from __future__ import unicode_literals

import argparse
import os
import signal

from dftimewolf import config

from dftimewolf.cli.recipes import local_plaso

from dftimewolf.lib import utils as dftw_utils

from dftimewolf.lib.collectors import filesystem
from dftimewolf.lib.exporters import timesketch
from dftimewolf.lib.exporters import local_filesystem
from dftimewolf.lib.processors import localplaso

from dftimewolf.lib.state import DFTimewolfState
from dftimewolf.lib.utils import DFTimewolfFormatterClass


signal.signal(signal.SIGINT, dftw_utils.signal_handler)

config.Config.register_module(filesystem.FilesystemCollector)
config.Config.register_module(localplaso.LocalPlasoProcessor)
config.Config.register_module(timesketch.TimesketchExporter)
config.Config.register_module(local_filesystem.LocalFilesystemCopy)

# Try to open config.json and load configuration data from it.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
USER_DIR = os.path.expanduser('~')
config.Config.load_extra(os.path.join(ROOT_DIR, 'config.json'))
config.Config.load_extra(os.path.join(USER_DIR, '.dftimewolfrc'))

config.Config.register_recipe(local_plaso)

# TODO(tomchop) Change the print statements by a better logging / display system


def generate_help():
  """Generates help text with alphabetically sorted recipes."""
  help_text = '\nAvailable recipes:\n\n'
  recipes = config.Config.get_registered_recipes()
  for contents, _, _ in sorted(recipes, key=lambda k: k[0]['name']):
    help_text += ' {0:<35s}{1:s}\n'.format(
        contents['name'], contents.get('short_description', 'No description'))
  return help_text


def main():
  """Main function for DFTimewolf."""
  parser = argparse.ArgumentParser(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      description=generate_help())

  subparsers = parser.add_subparsers()

  for registered_recipe in config.Config.get_registered_recipes():
    recipe, recipe_args, documentation = registered_recipe
    subparser = subparsers.add_parser(
        recipe['name'],
        formatter_class=DFTimewolfFormatterClass,
        description='{0:s}'.format(documentation))
    subparser.set_defaults(recipe=recipe)
    for switch, help_text, default in recipe_args:
      subparser.add_argument(switch, help=help_text, default=default)
    # Override recipe defaults with those specified in Config
    # so that they can in turn be overridden in the commandline
    subparser.set_defaults(**config.Config.get_extra())

  args = parser.parse_args()
  recipe = args.recipe

  console_out = dftw_utils.DFTimewolfConsoleOutput(
      sender='DFTimewolfCli', verbose=True)

  # Thread all collectors.
  console_out.StdOut('Collectors:')
  state = DFTimewolfState()

  for module_description in recipe['modules']:
    # Combine CLI args with args from the recipe description
    new_args = dftw_utils.import_args_from_dict(
        module_description['args'], vars(args), config.Config)

    # Create the module object and start processing
    module_name = module_description['name']
    print 'Running module {0:s}'.format(module_name)
    module = config.Config.get_module(module_name)(state)
    module.setup(**new_args)
    state.check_errors()
    module.process()

    # Check for eventual errors and clean up after each round.
    state.check_errors()
    state.cleanup()

  print 'Recipe executed succesfully.'
  if state.input:
    print 'The last executed module generated unprocessed input; here it is:'
    print state.input


if __name__ == '__main__':
  main()
