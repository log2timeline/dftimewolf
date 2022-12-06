#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""dftimewolf main entrypoint."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
import curses
import logging
import os
import signal
import sys
from typing import TYPE_CHECKING, List, Optional, Dict, Any, cast
from dftimewolf.cli.curses_display_manager import CursesDisplayManager
from dftimewolf.cli.curses_display_manager import CDMStringIOWrapper

# pylint: disable=wrong-import-position
from dftimewolf.lib import logging_utils
from dftimewolf import config

from dftimewolf.lib import errors
from dftimewolf.lib import utils

if TYPE_CHECKING:
  from dftimewolf.lib import state as dftw_state

# pylint: disable=line-too-long
MODULES = {
  'AWSAccountCheck': 'dftimewolf.lib.preflights.cloud_token',
  'AWSCollector': 'dftimewolf.lib.collectors.aws',
  'AWSLogsCollector': 'dftimewolf.lib.collectors.aws_logging',
  'AWSSnapshotS3CopyCollector': 'dftimewolf.lib.collectors.aws_snapshot_s3_copy',
  'AWSVolumeSnapshotCollector': 'dftimewolf.lib.collectors.aws_volume_snapshot',
  'AzureCollector': 'dftimewolf.lib.collectors.azure',
  'AzureLogsCollector': 'dftimewolf.lib.collectors.azure_logging',
  'BigQueryCollector': 'dftimewolf.lib.collectors.bigquery',
  'FilesystemCollector': 'dftimewolf.lib.collectors.filesystem',
  'GCEDiskCopy': 'dftimewolf.lib.collectors.gce_disk_copy',
  'GCEDiskFromImage': 'dftimewolf.lib.exporters.gce_disk_from_image',
  'GCEForensicsVM': 'dftimewolf.lib.processors.gce_forensics_vm',
  'GCEImageFromDisk': 'dftimewolf.lib.exporters.gce_image_from_disk',
  'GCPCloudResourceTree': 'dftimewolf.lib.processors.gcp_cloud_resource_tree',
  'GCPLoggingTimesketch': 'dftimewolf.lib.processors.gcp_logging_timesketch',
  'GCPLogsCollector': 'dftimewolf.lib.collectors.gcp_logging',
  'GCPTokenCheck': 'dftimewolf.lib.preflights.cloud_token',
  'GCSToGCEImage': 'dftimewolf.lib.exporters.gcs_to_gce_image',
  'GoogleCloudDiskExport': 'dftimewolf.lib.exporters.gce_disk_export',
  'GoogleCloudDiskExportStream': 'dftimewolf.lib.exporters.gce_disk_export_dd',
  'GoogleSheetsCollector': 'dftimewolf.lib.collectors.gsheets',
  'GrepperSearch': 'dftimewolf.lib.processors.grepper',
  'GRRArtifactCollector': 'dftimewolf.lib.collectors.grr_hosts',
  'GRRFileCollector': 'dftimewolf.lib.collectors.grr_hosts',
  'GRRFlowCollector': 'dftimewolf.lib.collectors.grr_hosts',
  'GRRHuntArtifactCollector': 'dftimewolf.lib.collectors.grr_hunt',
  'GRRHuntDownloader': 'dftimewolf.lib.collectors.grr_hunt',
  'GRRHuntFileCollector': 'dftimewolf.lib.collectors.grr_hunt',
  'GRRHuntOsqueryCollector': 'dftimewolf.lib.collectors.grr_hunt',
  'GRRHuntOsqueryDownloader': 'dftimewolf.lib.collectors.grr_hunt',
  'GRROsqueryCollector': 'dftimewolf.lib.collectors.grr_hosts',
  'GRRTimelineCollector': 'dftimewolf.lib.collectors.grr_hosts',
  'GRRYaraScanner': 'dftimewolf.lib.collectors.grr_hosts',
  'LocalFilesystemCopy': 'dftimewolf.lib.exporters.local_filesystem',
  'LocalPlasoProcessor': 'dftimewolf.lib.processors.localplaso',
  'OsqueryCollector': 'dftimewolf.lib.collectors.osquery',
  'S3ToGCSCopy': 'dftimewolf.lib.exporters.s3_to_gcs',
  'SanityChecks': 'dftimewolf.lib.preflights.sanity_checks',
  'SCPExporter': 'dftimewolf.lib.exporters.scp_ex',
  'SSHMultiplexer': 'dftimewolf.lib.preflights.ssh_multiplexer',
  'TimesketchEnhancer': 'dftimewolf.lib.enhancers.timesketch',
  'TimesketchExporter': 'dftimewolf.lib.exporters.timesketch',
  'TurbiniaArtifactProcessor': 'dftimewolf.lib.processors.turbinia_artifact',
  'TurbiniaGCPProcessor': 'dftimewolf.lib.processors.turbinia_gcp',
  'VTCollector' : 'dftimewolf.lib.collectors.virustotal',
  'WorkspaceAuditCollector': 'dftimewolf.lib.collectors.workspace_audit',
  'WorkspaceAuditTimesketch': 'dftimewolf.lib.processors.workspace_audit_timesketch',
  'YetiYaraCollector': 'dftimewolf.lib.collectors.yara'

}
# pylint: enable=line-too-long

from dftimewolf.lib.recipes import manager as recipes_manager
from dftimewolf.lib.state import DFTimewolfState, DFTimewolfStateWithCDM

logger = cast(logging_utils.WolfLogger, logging.getLogger('dftimewolf'))

class DFTimewolfTool(object):
  """DFTimewolf tool."""

  _state: "dftw_state.DFTimewolfState" # for pytype

  _DEFAULT_DATA_FILES_PATH = os.path.join(
      os.sep, 'usr', 'local', 'share', 'dftimewolf')

  def __init__(self, cdm: Optional[CursesDisplayManager] = None) -> None:
    """Initializes a DFTimewolf tool."""
    super(DFTimewolfTool, self).__init__()
    self._command_line_options: Optional[argparse.Namespace]
    self._data_files_path = ''
    self._recipes_manager = recipes_manager.RecipesManager()
    self._recipe = {}  # type: Dict[str, Any]
    self.cdm = cdm

    self._DetermineDataFilesPath()

  @property
  def state(self) -> "dftw_state.DFTimewolfState":
    """Returns the internal state object."""
    return self._state

  def _AddRecipeOptions(self, argument_parser: argparse.ArgumentParser) -> None:
    """Adds the recipe options to the argument group.

    Args:
      argument_parser (argparse.ArgumentParser): argparse argument parser.
    """
    subparsers = argument_parser.add_subparsers()

    for recipe in self._recipes_manager.GetRecipes():
      description = recipe.description
      subparser = subparsers.add_parser(
          recipe.name, formatter_class=utils.DFTimewolfFormatterClass,
          description=description)
      subparser.set_defaults(recipe=recipe.contents)

      for switch, help_text, default in recipe.args:
        if isinstance(default, bool):
          subparser.add_argument(switch, help=help_text, default=default,
                                 action='store_true')
        else:
          subparser.add_argument(switch, help=help_text, default=default)

      # Override recipe defaults with those specified in Config
      # so that they can in turn be overridden in the commandline
      subparser.set_defaults(**config.Config.GetExtra())

  def _DetermineDataFilesPath(self) -> None:
    """Determines the data files path.

    Data path is specified in the DFTIMEWOLF_DATA environment variable. If the
    variable is not specified, dfTimewolf checks if any of the following
    locations are valid:

    * Cloned repository base
    * Local package data files
    * sys.prefix
    * Hardcoded default /usr/local/share
    """

    data_files_path = os.environ.get('DFTIMEWOLF_DATA')

    if not data_files_path or not os.path.isdir(data_files_path):
      # Figure out if the script is running out of a cloned repository
      data_files_path = os.path.realpath(__file__)
      data_files_path = os.path.dirname(data_files_path)
      data_files_path = os.path.dirname(data_files_path)
      data_files_path = os.path.dirname(data_files_path)
      data_files_path = os.path.join(data_files_path, 'data')

      # Use local package data files (python setup.py install)
      if not os.path.isdir(data_files_path):
        data_files_path = os.path.dirname(data_files_path)
        data_files_path = os.path.join(data_files_path, 'share', 'dftimewolf')

      # Use sys.prefix for user installs (e.g. pip install ...)
      if not os.path.isdir(data_files_path):
        data_files_path = os.path.join(sys.prefix, 'share', 'dftimewolf')

      # If all else fails, fall back to hardcoded default
      if not os.path.isdir(data_files_path):
        logger.debug('{0:s} not found, defaulting to /usr/local/share'.format(
            data_files_path))
        data_files_path = self._DEFAULT_DATA_FILES_PATH

    logger.debug("Recipe data path: {0:s}".format(data_files_path))
    self._data_files_path = data_files_path

  def _GenerateHelpText(self) -> str:
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

  def _LoadConfigurationFromFile(self, configuration_file_path: str) -> None:
    """Loads a configuration from file.

    Args:
      configuration_file_path (str): path of the configuration file.
    """
    try:
      if config.Config.LoadExtra(configuration_file_path):
        logger.debug('Configuration loaded from: {0:s}'.format(
            configuration_file_path))

    except errors.BadConfigurationError as exception:
      logger.warning('{0!s}'.format(exception))

  def LoadConfiguration(self) -> None:
    """Loads the configuration.

    The following paths are tried. Values loaded last take precedence.

    * <_data_files_path>/config.json
    * /etc/dftimewolf.conf
    * /usr/share/dftimewolf/dftimewolf.conf
    * ~/.dftimewolfrc
    * If set, wherever the DFTIMEWOLF_CONFIG environment variable points to.

    """
    configuration_file_path = os.path.join(self._data_files_path, 'config.json')
    self._LoadConfigurationFromFile(configuration_file_path)

    configuration_file_path = os.path.join('/', 'etc', 'dftimewolf.conf')
    self._LoadConfigurationFromFile(configuration_file_path)

    configuration_file_path = os.path.join(
        '/', 'usr', 'share', 'dftimewolf', 'dftimewolf.conf')
    self._LoadConfigurationFromFile(configuration_file_path)

    user_directory = os.path.expanduser('~')
    configuration_file_path = os.path.join(user_directory, '.dftimewolfrc')
    self._LoadConfigurationFromFile(configuration_file_path)

    env_config = os.environ.get('DFTIMEWOLF_CONFIG')
    if env_config:
      self._LoadConfigurationFromFile(env_config)

  def ParseArguments(self, arguments: List[str]) -> None:
    """Parses the command line arguments.

    Args:
      arguments (list[str]): command line arguments.

    Raises:
      CommandLineParseError: If arguments could not be parsed.
    """
    help_text = self._GenerateHelpText()

    argument_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=help_text)

    self._AddRecipeOptions(argument_parser)

    self._command_line_options = argument_parser.parse_args(arguments)

    if not getattr(self._command_line_options, 'recipe', None):
      error_message = '\nPlease specify a recipe.\n' + help_text
      raise errors.CommandLineParseError(error_message)

    self._recipe = self._command_line_options.recipe

    if self.cdm:
      self._state = DFTimewolfStateWithCDM(config.Config, self.cdm)
    else:
      self._state = DFTimewolfState(config.Config)
    logger.info('Loading recipe {0:s}...'.format(self._recipe['name']))
    # Raises errors.RecipeParseError on error.
    self._state.LoadRecipe(self._recipe, MODULES)

    module_cnt = len(self._recipe.get('modules', [])) + \
                 len(self._recipe.get('preflights', []))
    logger.info('Loaded recipe {0:s} with {1:d} modules'.format(
        self._recipe['name'], module_cnt))

    self._state.command_line_options = vars(self._command_line_options)

  def RunPreflights(self) -> None:
    """Runs preflight modules."""
    logger.info('Running preflights...')
    self._state.RunPreflights()

  def ReadRecipes(self) -> None:
    """Reads the recipe files."""
    if os.path.isdir(self._data_files_path):
      recipes_path = os.path.join(self._data_files_path, 'recipes')
      if os.path.isdir(recipes_path):
        self._recipes_manager.ReadRecipesFromDirectory(recipes_path)

  def RunModules(self) -> None:
    """Runs the modules."""
    logger.info('Running modules...')
    self._state.RunModules()
    logger.info('Recipe {0:s} executed successfully!'.format(
        self._recipe['name']))

  def SetupModules(self) -> None:
    """Sets up the modules."""
    # TODO: refactor to only load modules that are used by the recipe.

    logger.info('Setting up modules...')
    self._state.SetupModules()
    logger.info('Modules successfully set up!')

  def CleanUpPreflights(self) -> None:
    """Calls the preflight's CleanUp functions."""
    self._state.CleanUpPreflights()

  def PrintStats(self) -> None:
    """Prints collected stats if existing."""
    stat_entries = self._state.GetStats()
    if not stat_entries:
      logger.info('No statistics collected during execution.')

    logger.info(f'{len(stat_entries)} stat entries collected during execution.')
    for entry in stat_entries:
      logger.debug(f'[{entry.module_name} ({entry.module_type})] {entry.stats}')

  def ExportStats(self) -> None:
    """Exports collected stats if existing. Default behavior is to log."""
    self.PrintStats()

  def RecipesManager(self) -> recipes_manager.RecipesManager:
    """Returns the recipes manager."""
    return self._recipes_manager


def SignalHandler(*unused_argvs: Any) -> None:
  """Catches Ctrl + C to exit cleanly."""
  sys.stderr.write("\nCtrl^C caught, bailing...\n")

  try:
    curses.nocbreak()
    curses.echo()
    curses.endwin()
  except curses.error:
    pass

  sys.exit(1)


def SetupLogging(stdout_log: bool = False) -> None:
  """Sets up a logging handler with dftimewolf's custom formatter."""
  # Add a custom level name
  logging.addLevelName(logging_utils.SUCCESS, 'SUCCESS')

  # Clear root handlers (for dependencies that are setting them)
  root_log = logging.getLogger()
  root_log.handlers = []

  # Add a silent default stream handler, this is automatically set
  # when other libraries call logging.info() or similar methods.
  root_handler = logging.StreamHandler(stream=sys.stdout)
  root_handler.addFilter(lambda x: False)
  root_log.addHandler(root_handler)

  # We want all DEBUG messages and above.
  # TODO(tomchop): Consider making this a parameter in the future.
  logger.setLevel(logging.DEBUG)
  logger.propagate = False

  # File handler needs go be added first because it doesn't format messages
  # with color
  file_handler = logging.FileHandler(logging_utils.DEFAULT_LOG_FILE)
  file_handler.setFormatter(logging_utils.WolfFormatter(colorize=False))
  logger.addHandler(file_handler)

  if stdout_log:
    console_handler = logging.StreamHandler(stream=sys.stdout)
    colorize = not bool(os.environ.get('DFTIMEWOLF_NO_RAINBOW'))
    console_handler.setFormatter(logging_utils.WolfFormatter(colorize=colorize))
    logger.addHandler(console_handler)
    logger.debug(f'Logging to stdout and {logging_utils.DEFAULT_LOG_FILE}')
  else:
    logger.debug(f'Logging to {logging_utils.DEFAULT_LOG_FILE}')

  logger.success('Success!')


def RunTool(cdm: Optional[CursesDisplayManager] = None) -> bool:
  """
  Runs DFTimewolfTool.

  Returns:
    bool: True if DFTimewolf could be run successfully, False otherwise.
  """
  version_tuple = (sys.version_info[0], sys.version_info[1])
  if version_tuple[0] != 3 or version_tuple < (3, 6):
    logger.critical(('Unsupported Python version: {0:s}, version 3.6 or higher '
                     'required.').format(sys.version))
    return False

  tool = DFTimewolfTool(cdm)

  # TODO: log errors if this fails.
  tool.LoadConfiguration()

  try:
    tool.ReadRecipes()
  except (KeyError, errors.RecipeParseError, errors.CriticalError) as exception:
    if cdm:
      cdm.EnqueueMessage('dftimewolf', str(exception), True)
    logger.critical(str(exception))
    return False

  try:
    tool.ParseArguments(sys.argv[1:])
  except (errors.CommandLineParseError,
          errors.RecipeParseError,
          errors.CriticalError) as exception:
    if cdm:
      cdm.EnqueueMessage('dftimewolf', str(exception), True)
    logger.critical(str(exception))
    return False

  tool.state.LogExecutionPlan()

  tool.RunPreflights()

  try:
    tool.SetupModules()
  except errors.CriticalError as exception:
    if cdm:
      cdm.EnqueueMessage('dftimewolf', str(exception), True)
    logger.critical(str(exception))
    return False

  try:
    tool.RunModules()
  except errors.CriticalError as exception:
    if cdm:
      cdm.EnqueueMessage('dftimewolf', str(exception), True)
    logger.critical(str(exception))
    return False

  tool.CleanUpPreflights()
  tool.ExportStats()

  return True


def Main() -> bool:
  """Main function for DFTimewolf.

  Returns:
    bool: True if DFTimewolf could be run successfully, False otherwise."""
  no_curses = bool(os.environ.get('DFTIMEWOLF_NO_CURSES'))

  SetupLogging(no_curses)

  if any([no_curses, '-h' in sys.argv, '--help' in sys.argv]):
    return RunTool()

  cursesdisplaymanager = CursesDisplayManager()
  cursesdisplaymanager.StartCurses()
  cursesdisplaymanager.EnqueueMessage(
    'dftimewolf', f'Debug log: {logging_utils.DEFAULT_LOG_FILE}')

  stdout_null = open(os.devnull, "w")
  stderr_sio = CDMStringIOWrapper(
      'stderr', True, cursesdisplaymanager.EnqueueMessage)
  exit_code = False

  try:
    with redirect_stdout(stdout_null), redirect_stderr(stderr_sio):
      exit_code = RunTool(cursesdisplaymanager)
  except Exception as e:  # pylint: disable=broad-except
    cursesdisplaymanager.SetException(e)
    cursesdisplaymanager.Draw()
  finally:
    cursesdisplaymanager.Draw()
    cursesdisplaymanager.EndCurses()
    cursesdisplaymanager.PrintMessages()

  return exit_code

if __name__ == '__main__':
  signal.signal(signal.SIGINT, SignalHandler)
  if Main():
    sys.exit(0)
  else:
    sys.exit(1)
