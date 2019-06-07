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

from dftimewolf.cli.recipes import gcp_turbinia
from dftimewolf.cli.recipes import gcp_turbinia_import
from dftimewolf.cli.recipes import grr_artifact_hosts
from dftimewolf.cli.recipes import grr_flow_download
from dftimewolf.cli.recipes import grr_fetch_files
from dftimewolf.cli.recipes import grr_hunt_artifacts
from dftimewolf.cli.recipes import grr_hunt_file
from dftimewolf.cli.recipes import grr_huntresults_plaso_timesketch
from dftimewolf.cli.recipes import local_plaso
from dftimewolf.cli.recipes import timesketch_upload
from dftimewolf.cli.recipes import artifact_grep
from dftimewolf.cli.recipes import stackdriver_collect

from dftimewolf.lib import utils


if not _ASKING_FOR_HELP:
  from dftimewolf.lib.collectors import filesystem
  from dftimewolf.lib.collectors import grr_hosts
  from dftimewolf.lib.collectors import grr_hunt
  from dftimewolf.lib.exporters import timesketch
  from dftimewolf.lib.exporters import local_filesystem
  from dftimewolf.lib.processors import localplaso
  from dftimewolf.lib.processors import turbinia
  from dftimewolf.lib.processors import grepper
  from dftimewolf.lib.collectors.gcloud import GoogleCloudCollector

from dftimewolf.lib.state import DFTimewolfState

signal.signal(signal.SIGINT, utils.signal_handler)


if not _ASKING_FOR_HELP:
  config.Config.register_module(filesystem.FilesystemCollector)
  config.Config.register_module(localplaso.LocalPlasoProcessor)
  config.Config.register_module(timesketch.TimesketchExporter)
  config.Config.register_module(GoogleCloudCollector)

  config.Config.register_module(grr_hosts.GRRArtifactCollector)
  config.Config.register_module(grr_hosts.GRRFileCollector)
  config.Config.register_module(grr_hosts.GRRFlowCollector)
  config.Config.register_module(grr_hunt.GRRHuntArtifactCollector)
  config.Config.register_module(grr_hunt.GRRHuntFileCollector)
  config.Config.register_module(grr_hunt.GRRHuntDownloader)

  config.Config.register_module(timesketch.TimesketchExporter)
  config.Config.register_module(local_filesystem.LocalFilesystemCopy)
  config.Config.register_module(turbinia.TurbiniaProcessor)
  config.Config.register_module(grepper.GrepperSearch)


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
config.Config.register_recipe(gcp_turbinia)
config.Config.register_recipe(gcp_turbinia_import)
config.Config.register_recipe(artifact_grep)
config.Config.register_recipe(stackdriver_collect)

# TODO(tomchop) Change the print statements by a better logging / display system


def generate_help():
  """Generates help text with alphabetically sorted recipes."""
  help_text = '\nAvailable recipes:\n\n'
  for recipe in config.Config.get_registered_recipes():
    short_description = recipe.contents.get(
        'short_description', 'No description')
    help_text += ' {0:<35s}{1:s}\n'.format(recipe.name, short_description)
  return help_text


def main():
  """Main function for DFTimewolf."""
  parser = argparse.ArgumentParser(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      description=generate_help())

  subparsers = parser.add_subparsers()

  for recipe in config.Config.get_registered_recipes():
    subparser = subparsers.add_parser(
        recipe.name, formatter_class=utils.DFTimewolfFormatterClass,
        description='{0:s}'.format(recipe.description))
    subparser.set_defaults(recipe=recipe.contents)

    for switch, help_text, default in recipe.args:
      subparser.add_argument(switch, help=help_text, default=default)
    # Override recipe defaults with those specified in Config
    # so that they can in turn be overridden in the commandline
    subparser.set_defaults(**config.Config.get_extra())

  args = parser.parse_args()
  recipe = args.recipe

  state = DFTimewolfState(config.Config)
  print('Loading recipes...')
  state.load_recipe(recipe)
  print('Loaded recipe {0:s} with {1:d} modules'.format(
      recipe['name'], len(recipe['modules'])))

  print('Setting up modules...')
  state.setup_modules(args)
  print('Modules successfully set up!')

  print('Running modules...')
  state.run_modules()
  print('Recipe {0:s} executed successfully.'.format(recipe['name']))


if __name__ == '__main__':
  main()
