"""Timeflow CLI tool to collect artifacts.

timeflow_recipes aims to replace timeflow_cli. It uses recipes defined in
timeflow/cli/recipes to orchestrate collectors, processors and exporters.


Usage:

$ timeflow_recipes <recipe_name> <recipe_parameters>


You can get help on recipe parameters using:

$ timeflow_recipes <recipe_name> --help


Usage example (for "corp_hosts" recipe):

$ timeflow_recipes local_plaso tomchop.yourorg.com testing
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
import re

from timeflow.cli.recipes import local_plaso

# It's better to load these in the client since we want to keep recipes as
# descriptive as possible.
from timeflow.lib import utils as timeflow_utils
from timeflow.lib.collectors import filesystem
from timeflow.lib.exporters import timesketch
from timeflow.lib.processors import localplaso


COLLECTORS = {
    'filesystem': filesystem.FilesystemCollector,
}

PROCESSORS = {
    'localplaso': localplaso.LocalPlasoProcessor,
}

EXPORTERS = {
    'timesketch': timesketch.TimesketchExporter
}

RECIPES = {
    'local_plaso': local_plaso,
}


def import_args_from_cli(elt, args):
  """Replaces some arguments by those specified in CLI.

  This function will be recursively called on a dictionary looking for any
  value staring with a "$" character. If found, the value will be replaced
  by the attribute in "args" of the same name.

  Args:
    elt: dictionary containing arguments.See examples in timeflow/cli/recipes/
    args: argparse parse_args() object

  Returns:
    The first caller of the function will receive a dictionary in which the
    values starting with "$" are replaced by the parameters in args.
  """

  if isinstance(elt, (str, unicode)):
    sub = re.match(r'\$(\w+)', str(elt))
    if sub:
      return getattr(args, sub.group(1))
    return elt
  elif isinstance(elt, list):
    return [import_args_from_cli(item, args) for item in elt]
  elif isinstance(elt, dict):
    return {key: import_args_from_cli(val, args) for key, val in elt.items()}
  return elt


def main():
  """Main function for Timeflow."""

  parser = argparse.ArgumentParser()

  subparsers = parser.add_subparsers(
      title=u'Available recipes',
      description=u'List of currently loaded recipes',
      help=u'Recipe-specific help')

  for recipe in RECIPES.values():
    subparser = subparsers.add_parser(
        recipe.RECIPE[u'name'],
        description=u'{0:s}'.format(recipe.__doc__))
    subparser.set_defaults(recipe=recipe)
    for switch, help_text in recipe.ARGS:
      subparser.add_argument(switch, help=help_text)

  args = parser.parse_args()
  recipe = args.recipe.RECIPE

  console_out = timeflow_utils.TimeflowConsoleOutput(
      sender=u'TimeflowCli', verbose=True)

  # COLLECTORS
  # Thread collectors
  console_out.StdOut(u'Collectors:')
  for collector in recipe['collectors']:
    console_out.StdOut(u'  {0:s}'.format(collector[u'name']))

  collector_objs = []
  for collector in recipe[u'collectors']:
    new_args = import_args_from_cli(collector[u'args'], args)
    collector_cls = COLLECTORS[collector[u'name']]
    collector_objs.extend(collector_cls.launch_collector(**new_args))

  # Wait for collectors to finish and collect output
  collector_output = []
  for collector_obj in collector_objs:
    collector_obj.join()
    collector_output.extend(collector_obj.output)

  # PROCESSORS
  # Thread processors
  console_out.StdOut(u'Processors:')
  for processor in recipe[u'processors']:
    console_out.StdOut(u'  {0:s}'.format(processor[u'name']))

  processor_objs = []
  for processor in recipe[u'processors']:
    new_args = import_args_from_cli(processor[u'args'], args)
    new_args[u'collector_output'] = collector_output
    processor_class = PROCESSORS[processor[u'name']]
    processor_objs.extend(processor_class.launch_processor(**new_args))

  # Wait for processors to finish and collect output
  processor_output = []
  for processor in processor_objs:
    processor.join()
    processor_output.extend(processor.output)

  # EXPORTERS
  # Thread exporters
  console_out.StdOut(u'Exporters:')
  for exporter in recipe[u'exporters']:
    console_out.StdOut(u'  {0:s}'.format(exporter[u'name']))

  exporter_objs = []
  for exporter in recipe[u'exporters']:
    new_args = import_args_from_cli(exporter[u'args'], args)
    new_args[u'processor_output'] = processor_output
    exporter_class = EXPORTERS[exporter[u'name']]
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
