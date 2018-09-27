# -*- coding: utf-8 -*-
"""dftimewolf main entrypoint."""

from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import signal

from dftimewolf import config

from dftimewolf.cli.recipes import local_plaso
from dftimewolf.cli.recipes import grr_artifact_hosts
from dftimewolf.cli.recipes import grr_flow_download
from dftimewolf.cli.recipes import grr_fetch_files
from dftimewolf.cli.recipes import grr_hunt_artifacts
from dftimewolf.cli.recipes import grr_hunt_file
from dftimewolf.cli.recipes import grr_huntresults_plaso_timesketch
from dftimewolf.cli.recipes import timesketch_upload
from dftimewolf.cli.recipes import insider_triage

from dftimewolf.lib import utils

from dftimewolf.lib.collectors import filesystem
from dftimewolf.lib.collectors import grr_hosts
from dftimewolf.lib.collectors import grr_hunt
from dftimewolf.lib.exporters import timesketch
from dftimewolf.lib.exporters import local_filesystem
from dftimewolf.lib.processors import localplaso
from dftimewolf.lib.processors import grepper

from dftimewolf.lib.state import DFTimewolfState
from dftimewolf.lib.errors import DFTimewolfError

signal.signal(signal.SIGINT, utils.signal_handler)

config.Config.register_module(filesystem.FilesystemCollector)
config.Config.register_module(localplaso.LocalPlasoProcessor)
config.Config.register_module(timesketch.TimesketchExporter)
config.Config.register_module(grepper.GrepperSearch)

config.Config.register_module(grr_hosts.GRRArtifactCollector)
config.Config.register_module(grr_hosts.GRRFileCollector)
config.Config.register_module(grr_hosts.GRRFlowCollector)
config.Config.register_module(grr_hunt.GRRHuntArtifactCollector)
config.Config.register_module(grr_hunt.GRRHuntFileCollector)
config.Config.register_module(grr_hunt.GRRHuntDownloader)

config.Config.register_module(timesketch.TimesketchExporter)
config.Config.register_module(local_filesystem.LocalFilesystemCopy)

# Try to open config.json and load configuration data from it.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
USER_DIR = os.path.expanduser('~')
config.Config.load_extra(os.path.join(ROOT_DIR, 'config.json'))
config.Config.load_extra(os.path.join(USER_DIR, '.dftimewolfrc'))
config.Config.load_extra(os.path.join('/', 'etc', 'dftimewolf.conf'))

config.Config.register_recipe(local_plaso)
config.Config.register_recipe(grr_artifact_hosts)
config.Config.register_recipe(grr_flow_download)
config.Config.register_recipe(grr_fetch_files)
config.Config.register_recipe(grr_hunt_artifacts)
config.Config.register_recipe(grr_hunt_file)
config.Config.register_recipe(grr_huntresults_plaso_timesketch)
config.Config.register_recipe(timesketch_upload)
config.Config.register_recipe(insider_triage)

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
        formatter_class=utils.DFTimewolfFormatterClass,
        description='{0:s}'.format(documentation))
    subparser.set_defaults(recipe=recipe)
    for switch, help_text, default in recipe_args:
      subparser.add_argument(switch, help=help_text, default=default)
    # Override recipe defaults with those specified in Config
    # so that they can in turn be overridden in the commandline
    subparser.set_defaults(**config.Config.get_extra())

  args = parser.parse_args()
  recipe = args.recipe

  # Thread all collectors.
  state = DFTimewolfState()

  for module_description in recipe['modules']:
    # Combine CLI args with args from the recipe description
    new_args = utils.import_args_from_dict(
        module_description['args'], vars(args), config.Config)

    # Create the module object and start processing
    module_name = module_description['name']
    print('Running module {0:s}'.format(module_name))
    module = config.Config.get_module(module_name)(state)
    module.setup(**new_args)
    state.check_errors()
    try:
      module.process()
    except DFTimewolfError as error:
      state.add_error(error.message, critical=True)

    # Check for eventual errors and clean up after each round.
    state.check_errors()
    state.cleanup()

  print('Recipe executed successfully.')


if __name__ == '__main__':
  main()
