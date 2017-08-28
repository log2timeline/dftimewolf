"""DFTimewolf CLI tool to collect artifacts.

dftimewolf_recipes uses recipes defined in dftimewolf/cli/recipes to orchestrate
collectors, processors and exporters.


Usage:

$ dftimewolf_recipes <recipe_name> <recipe_parameters>


You can get help on recipe parameters using:

$ dftimewolf_recipes <recipe_name> --help


Usage example (for "corp_hosts" recipe):

$ dftimewolf_recipes local_plaso tomchop.yourorg.com testing
Collectors:
  filesystem
<collector verbose output>
Processors:
  localplaso
<processor verbose output>
Exporters:
  timesketch
<exporter output>
New sketch created: 244
Your Timesketch URL is: https://timesketch.yourorg.com/sketch/244/
Recipe local_plaso executed successfully

"""

__author__ = u'tomchop@google.com (Thomas Chopitea)'

import argparse
import os

from dftimewolf import config
from dftimewolf.lib import utils as dftw_utils

from dftimewolf.lib.collectors import filesystem
from dftimewolf.lib.processors import localplaso
from dftimewolf.lib.exporters import timesketch

from dftimewolf.cli.recipes import local_plaso

config.Config.register_collector(filesystem.FilesystemCollector)
config.Config.register_processor(localplaso.LocalPlasoProcessor)
config.Config.register_exporter(timesketch.TimesketchExporter)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
config_path = os.path.join(ROOT_DIR, 'config.json')
config.Config.load_extra(config_path)

config.Config.register_recipe(local_plaso)


def main():
  """Main function for DFTimewolf."""

  parser = argparse.ArgumentParser()

  subparsers = parser.add_subparsers(
      title=u'Available recipes',
      description=u'List of currently loaded recipes',
      help=u'Recipe-specific help')

  for recipe, recipe_args in config.Config.get_registered_recipes():
    subparser = subparsers.add_parser(
        recipe[u'name'],
        description=u'{0:s}'.format(recipe.__doc__))
    subparser.set_defaults(recipe=recipe)
    for switch, help_text in recipe_args:
      subparser.add_argument(switch, help=help_text)

  args = parser.parse_args()
  recipe = args.recipe

  console_out = dftw_utils.DFTimewolfConsoleOutput(
      sender=u'DFTimewolfCli', verbose=True)

  # COLLECTORS
  # Thread collectors
  console_out.StdOut(u'Collectors:')
  for collector in recipe['collectors']:
    console_out.StdOut(u'  {0:s}'.format(collector[u'name']))

  collector_objs = []
  for collector in recipe[u'collectors']:
    new_args = dftw_utils.import_args_from_dict(collector[u'args'], vars(args))
    collector_cls = config.Config.get_collector(collector[u'name'])
    collector_objs.extend(collector_cls.launch_collector(**new_args))

  # Wait for collectors to finish and collect output
  collector_output = []
  for collector_obj in collector_objs:
    collector_obj.join()
    collector_output.extend(collector_obj.results)

  if recipe[u'processors']:
    # PROCESSORS
    # Thread processors
    console_out.StdOut(u'Processors:')
    for processor in recipe[u'processors']:
      console_out.StdOut(u'  {0:s}'.format(processor[u'name']))

    processor_objs = []
    for processor in recipe[u'processors']:
      new_args = dftw_utils.import_args_from_dict(
          processor[u'args'], vars(args))
      new_args[u'collector_output'] = collector_output
      processor_class = config.Config.get_processor(processor[u'name'])
      processor_objs.extend(processor_class.launch_processor(**new_args))

    # Wait for processors to finish and collect output
    processor_output = []
    for processor in processor_objs:
      processor.join()
      processor_output.extend(processor.output)
  else:
    processor_output = collector_output

  # EXPORTERS
  # Thread exporters
  console_out.StdOut(u'Exporters:')
  for exporter in recipe[u'exporters']:
    console_out.StdOut(u'  {0:s}'.format(exporter[u'name']))

  exporter_objs = []
  for exporter in recipe[u'exporters']:
    new_args = dftw_utils.import_args_from_dict(exporter[u'args'], vars(args))
    new_args[u'processor_output'] = processor_output
    exporter_class = config.Config.get_exporter(exporter[u'name'])
    exporter_objs.extend(exporter_class.launch_exporter(**new_args))

  # Wait for exporters to finish
  exporter_output = []
  for exporter in exporter_objs:
    exporter.join()
    exporter_output.extend(exporter.output)

  console_out.StdOut(
      u'Recipe {0:s} executed successfully'.format(recipe[u'name']))

if __name__ == '__main__':
  main()
