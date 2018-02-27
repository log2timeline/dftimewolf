# -*- coding: utf-8 -*-
"""dftimewolf main entrypoint."""

from __future__ import unicode_literals

import argparse
import os
import signal

from dftimewolf import config

from dftimewolf.cli.recipes import grr_artifact_hosts
from dftimewolf.cli.recipes import grr_flow_download
from dftimewolf.cli.recipes import grr_hunt_artifacts
from dftimewolf.cli.recipes import grr_hunt_file
from dftimewolf.cli.recipes import grr_huntresults_plaso_timesketch
from dftimewolf.cli.recipes import local_plaso
from dftimewolf.cli.recipes import timesketch_upload

from dftimewolf.lib import utils as dftw_utils

from dftimewolf.lib.collectors import filesystem
from dftimewolf.lib.collectors import grr
from dftimewolf.lib.exporters import local_filesystem
from dftimewolf.lib.exporters import timesketch
from dftimewolf.lib.processors import localplaso
from dftimewolf.lib.utils import DFTimewolfFormatterClass


signal.signal(signal.SIGINT, dftw_utils.signal_handler)

config.Config.register_collector(filesystem.FilesystemCollector)
config.Config.register_collector(grr.GRRHuntArtifactCollector)
config.Config.register_collector(grr.GRRHuntFileCollector)
config.Config.register_collector(grr.GRRHuntDownloader)
config.Config.register_collector(grr.GRRArtifactCollector)
config.Config.register_collector(grr.GRRFileCollector)
config.Config.register_collector(grr.GRRFlowCollector)
config.Config.register_processor(localplaso.LocalPlasoProcessor)
config.Config.register_exporter(timesketch.TimesketchExporter)
config.Config.register_exporter(local_filesystem.LocalFilesystemExporter)

# Try to open config.json and load configuration data from it.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
USER_DIR = os.path.expanduser('~')
config.Config.load_extra(os.path.join(ROOT_DIR, 'config.json'))
config.Config.load_extra(os.path.join(USER_DIR, '.dftimewolfrc'))

config.Config.register_recipe(local_plaso)
config.Config.register_recipe(grr_artifact_hosts)
config.Config.register_recipe(grr_hunt_file)
config.Config.register_recipe(grr_hunt_artifacts)
config.Config.register_recipe(grr_huntresults_plaso_timesketch)
config.Config.register_recipe(grr_flow_download)
config.Config.register_recipe(timesketch_upload)


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
  for collector in recipe['collectors']:
    console_out.StdOut('  {0:s}'.format(collector['name']))

  collector_objects = []
  for collector in recipe['collectors']:
    new_args = dftw_utils.import_args_from_dict(
        collector['args'], vars(args), config.Config)
    collector_cls = config.Config.get_collector(collector['name'])
    collector_objects.extend(collector_cls.launch_collector(**new_args))

  # global_errors will contain any errors generated along the way by collectors,
  # producers or exporters.
  global_errors = []

  # Wait for collectors to finish and collect output.
  collector_output = []
  for collector_obj in collector_objects:
    collector_obj.join()
    collector_output.extend(collector_obj.results)
    if collector_obj.errors:
      # TODO(tomchop): Add name attributes in module objects
      error = (collector_obj.__class__.__name__, ', '.join(
          collector_obj.errors))
      global_errors.append(error)
      console_out.StdErr('ERROR:{0:s}:{1:s}\n'.format(*error))

  if recipe['processors']:
    # Thread processors.
    console_out.StdOut('Processors:')
    for processor in recipe['processors']:
      console_out.StdOut('  {0:s}'.format(processor['name']))

    processor_objs = []
    for processor in recipe['processors']:
      new_args = dftw_utils.import_args_from_dict(
          processor['args'], vars(args), config.Config)
      new_args['collector_output'] = collector_output
      processor_class = config.Config.get_processor(processor['name'])
      processor_objs.extend(processor_class.launch_processor(**new_args))

    # Wait for processors to finish and collect output
    processor_output = []
    for processor in processor_objs:
      processor.join()
      processor_output.extend(processor.output)
      if processor.errors:
        # Note: Should we fail if modules produce errors, or is warning the user
        # enough?
        # TODO(tomchop): Add name attributes in module objects.
        error = (processor.__class__.__name__, ', '.join(processor.errors))
        global_errors.append(error)
        console_out.StdErr('ERROR:{0:s}:{1:s}\n'.format(*error))

  else:
    processor_output = collector_output

  # Thread all exporters.
  if recipe['exporters']:
    console_out.StdOut('Exporters:')
    for exporter in recipe['exporters']:
      console_out.StdOut('  {0:s}'.format(exporter['name']))

    exporter_objs = []
    for exporter in recipe['exporters']:
      new_args = dftw_utils.import_args_from_dict(
          exporter['args'], vars(args), config.Config)
      new_args['processor_output'] = processor_output
      exporter_class = config.Config.get_exporter(exporter['name'])
      exporter_objs.extend(exporter_class.launch_exporter(**new_args))

    # Wait for exporters to finish.
    exporter_output = []
    for exporter in exporter_objs:
      exporter.join()
      exporter_output.extend(exporter.output)
      if exporter.errors:
        # TODO(tomchop): Add name attributes in module objects
        error = (exporter.__class__.__name__, ', '.join(exporter.errors))
        global_errors.append(error)
        console_out.StdErr('ERROR:{0:s}:{1:s}\n'.format(*error))
  else:
    exporter_output = processor_output

  if not global_errors:
    console_out.StdOut(
        'Recipe {0:s} executed successfully'.format(recipe['name']))
  else:
    console_out.StdOut(
        'Recipe {0:s} executed with {1:d} errors:'.format(
            recipe['name'], len(global_errors)))
    for error in global_errors:
      console_out.StdOut('  {0:s}: {1:s}'.format(*error))


if __name__ == '__main__':
  main()
