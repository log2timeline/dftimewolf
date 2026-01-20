#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""dftimewolf main entrypoint."""

import argparse
import datetime
import logging
import os
import signal
import sys
import time
import typing
import uuid

from typing import TYPE_CHECKING, List, Optional, Dict, Any, cast

from dftimewolf.lib.validators import manager as validators_manager

# The following import makes sure validators are registered.
from dftimewolf.lib import validators # pylint: disable=unused-import

# pylint: disable=wrong-import-position
from dftimewolf.lib import logging_utils
from dftimewolf.lib import telemetry
from dftimewolf import config
from dftimewolf.lib.modules import module_runner
from dftimewolf.lib import errors
from dftimewolf.lib import utils

if TYPE_CHECKING:
  from dftimewolf.lib import resources

TELEMETRY = telemetry

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
  'DataFrameToDiskExporter': 'dftimewolf.lib.exporters.df_to_filesystem',
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
  'GoogleDriveCollector': 'dftimewolf.lib.collectors.gdrive',
  'GoogleDriveExporter': 'dftimewolf.lib.exporters.gdrive',
  'GoogleSheetsCollector': 'dftimewolf.lib.collectors.gsheets',
  'GRRArtifactCollector': 'dftimewolf.lib.collectors.grr_hosts',
  'GRRFileCollector': 'dftimewolf.lib.collectors.grr_hosts',
  'GRRFlowCollector': 'dftimewolf.lib.collectors.grr_hosts',
  'GRRHuntArtifactCollector': 'dftimewolf.lib.collectors.grr_hunt',
  'GRRHuntDownloader': 'dftimewolf.lib.collectors.grr_hunt',
  'GRRHuntFileCollector': 'dftimewolf.lib.collectors.grr_hunt',
  'GRRHuntOsqueryCollector': 'dftimewolf.lib.collectors.grr_hunt',
  'GRRHuntOsqueryDownloader': 'dftimewolf.lib.collectors.grr_hunt',
  'GRRHuntYaraScanner': 'dftimewolf.lib.collectors.grr_hunt',
  'GRROsqueryCollector': 'dftimewolf.lib.collectors.grr_hosts',
  'GRRTimelineCollector': 'dftimewolf.lib.collectors.grr_hosts',
  'GRRYaraScanner': 'dftimewolf.lib.collectors.grr_hosts',
  'LocalFilesystemCopy': 'dftimewolf.lib.exporters.local_filesystem',
  'LocalPlasoProcessor': 'dftimewolf.lib.processors.localplaso',
  'LocalYaraCollector': 'dftimewolf.lib.collectors.yara',
  'OsqueryCollector': 'dftimewolf.lib.collectors.osquery',
  'S3ToGCSCopy': 'dftimewolf.lib.exporters.s3_to_gcs',
  'SSHMultiplexer': 'dftimewolf.lib.preflights.ssh_multiplexer',
  'TimesketchExporter': 'dftimewolf.lib.exporters.timesketch',
  'TimesketchSearchEventCollector': 'dftimewolf.lib.collectors.timesketch',
  'TurbiniaArtifactProcessor': 'dftimewolf.lib.processors.turbinia_artifact',
  'TurbiniaGCPProcessor': 'dftimewolf.lib.processors.turbinia_gcp',
  'VTCollector' : 'dftimewolf.lib.collectors.virustotal',
  'OpenRelikProcessor': 'dftimewolf.lib.processors.openrelik',
  'WorkspaceAuditCollector': 'dftimewolf.lib.collectors.workspace_audit',
  'WorkspaceAuditTimesketch': 'dftimewolf.lib.processors.workspace_audit_timesketch',
  'YetiYaraCollector': 'dftimewolf.lib.collectors.yara'
}
# pylint: enable=line-too-long

from dftimewolf.lib.recipes import manager as recipes_manager


logger = cast(logging_utils.WolfLogger, logging.getLogger('dftimewolf'))


class DFTimewolfTool(object):
  """DFTimewolf tool."""


  _DEFAULT_DATA_FILES_PATH = os.path.join(
      os.sep, 'usr', 'local', 'share', 'dftimewolf')

  def __init__(
      self,
      workflow_uuid: Optional[str] = None) -> None:
    """Initializes a DFTimewolf tool."""
    super(DFTimewolfTool, self).__init__()
    self._data_files_path = ''
    self._recipes_manager = recipes_manager.RecipesManager()
    self._recipe = {}  # type: Dict[str, Any]
    self._command_line_options = argparse.Namespace()
    self._running_args: dict[str, typing.Any] = {}
    self.dry_run = False
    if not workflow_uuid:
      workflow_uuid = str(uuid.uuid4())
    self.uuid = workflow_uuid

    self._telemetry = self.InitializeTelemetry()
    self._DetermineDataFilesPath()
    self._module_runner = module_runner.ModuleRunner(
        logger, self._telemetry, self.PublishMessage)

  def _AddRecipeOptions(self, argument_parser: argparse.ArgumentParser) -> None:
    """Adds the recipe options to the argument group.

    Args:
      argument_parser (argparse.ArgumentParser): argparse argument parser.
    """
    argument_parser.add_argument('--dry_run', help='Tool dry run',
                                 default=False, action='store_true')

    subparsers = argument_parser.add_subparsers()

    for recipe in self._recipes_manager.GetRecipes():
      description = recipe.description
      subparser = subparsers.add_parser(
          recipe.name, formatter_class=utils.DFTimewolfFormatterClass,
          description=description)
      subparser.set_defaults(recipe=recipe.contents)

      for args in recipe.args:
        if isinstance(args.default, bool):
          subparser.add_argument(args.switch, help=args.help_text,
                                 default=args.default, action='store_true')
        else:
          subparser.add_argument(args.switch, help=args.help_text,
                                 default=args.default)

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
    self.dry_run = self._command_line_options.dry_run

    self._telemetry.SetRecipeName(self._recipe['name'])

    logger.info('Loading recipe {0:s}...'.format(self._recipe['name']))
    # Raises errors.RecipeParseError on error.
    self._module_runner.LoadModules(self._recipe, MODULES)

    module_cnt = len(self._recipe.get('modules', [])) + \
                 len(self._recipe.get('preflights', []))
    logger.info('Loaded recipe {0:s} with {1:d} modules'.format(
        self._recipe['name'], module_cnt))

    self._running_args = vars(self._command_line_options)

  def ValidateArguments(self, dry_run: bool=False) -> None:
    """Validate the arguments.

    Args:
      dry_run: True if the tool is only testing parameters, False otherwise.

    Raises:
      errors.CriticalError: If one or more arguments could not be validated.
    """
    recipe = self._recipes_manager.Recipes()[self._recipe['name']]
    error_messages = []

    for arg in recipe.args:
      expanded_argument = self._SubstituteValidationParameters(arg)

      switch = expanded_argument.switch.replace('--', '')
      argument_mandatory = switch == arg.switch
      argument_value = self._running_args.get(switch)

      if argument_mandatory or argument_value is not None:
        try:
          valid_value = validators_manager.ValidatorsManager.Validate(
              argument_value, arg, dry_run)
          self._running_args[switch] = valid_value
        except errors.RecipeArgsValidationFailure as exception:
          error_messages.append(
              f'Invalid argument: "{arg.switch}" with value "{argument_value}".'
              f' Error: {str(exception)}')
        except errors.RecipeArgsValidatorError as exception:
          error_messages.append(
            f'Argument validation error: "{arg.switch}" with '
            f'value "{argument_value}". Error: '
            f'{str(exception)}')

    if error_messages:
      for message in error_messages:
        logger.critical(message)
      raise errors.CriticalError(
          'At least one argument failed validation')

  def InterpolateArgs(self):
    """Interpolate config values and CLI args into the recipe args."""
    for module in (self._recipe.get('preflights', []) +
                   self._recipe.get('modules', [])):
      module['args'] = utils.ImportArgsFromDict(module['args'],
                                                self._running_args,
                                                config.Config)

  def _SubstituteValidationParameters(
      self, arg: "resources.RecipeArgument") -> "resources.RecipeArgument":
    """Replaces parameters in the format specification of an argument validator.

    Args:
      arg: recipe argument to replace parameters in.

    Returns:
      recipe argument with placeholders replaced.
    """
    if arg.validation_params is not None:
      for key, value in arg.validation_params.items():
        if isinstance(value, str) and '@' in value:
          to_substitute = value.replace('@', '')
          if to_substitute in self._running_args:
            arg.validation_params[key] = (
                self._running_args[to_substitute])
    return arg

  def ReadRecipes(self) -> None:
    """Reads the recipe files."""
    if os.path.isdir(self._data_files_path):
      recipes_path = os.path.join(self._data_files_path, 'recipes')
      if os.path.isdir(recipes_path):
        self._recipes_manager.ReadRecipesFromDirectory(recipes_path)

  def RunAllModules(self) -> None:
    """Runs the modules."""
    logger.info('Running modules...')
    self._module_runner.Run(self._running_args)
    logger.info('Modules run successfully!')

  def LogTelemetry(self) -> None:
    """Prints collected telemetry if existing."""

    for line in self._telemetry.FormatTelemetry().split('\n'):
      logger.debug(line)

  def RecipesManager(self) -> recipes_manager.RecipesManager:
    """Returns the recipes manager."""
    return self._recipes_manager

  def InitializeTelemetry(self) -> telemetry.BaseTelemetry:
    """Initializes the telemetry object."""
    return telemetry.GetTelemetry(uuid=self.uuid)

  def PublishMessage(
      self, source: str, message: str, is_error: bool = False) -> None:
    """Receives a message for publishing.

    The base class does nothing with this (as the method in module also logs the
    message). This method exists to be overridden for other UIs.

    Args:
      source: The source of the message.
      message: The message content.
      is_error: True if the message is an error message, False otherwise.
    """

  def LogExecutionPlan(self) -> None:
    """log the execution plan."""
    self._module_runner.LogExecutionPlan()


def SignalHandler(*unused_argvs: Any) -> None:
  """Catches Ctrl + C to exit cleanly."""
  sys.stderr.write("\nCtrl^C caught, bailing...\n")

  sys.exit(1)


def SetupLogging(stdout_log: bool = False) -> None:
  """Sets up a logging handler with dftimewolf's custom formatter.

  Levels should be as follows:
  * The logger is DEBUG
  * The file handler is DEBUG
  * The stdout stream handler is INFO, unless the env var DFTIMEWOLF_DEBUG=1

  Args:
    stdout_log (bool): Whether to log to stdout as well as a file.
  """
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

  logger.setLevel(logging.DEBUG)
  logger.propagate = False

  # File handler needs go be added first because it doesn't format messages
  # with color
  file_handler = logging.FileHandler(logging_utils.DEFAULT_LOG_FILE)
  file_handler.setFormatter(logging_utils.WolfFormatter(colorize=False))
  file_handler.setLevel(logging.DEBUG)  # Always log DEBUG logs to files.
  logger.addHandler(file_handler)

  if stdout_log:
    console_handler = logging.StreamHandler(stream=sys.stdout)
    colorize = not bool(os.environ.get('DFTIMEWOLF_NO_RAINBOW'))
    console_handler.setFormatter(logging_utils.WolfFormatter(colorize=colorize))
    console_handler.setLevel(logging.DEBUG
                             if os.environ.get("DFTIMEWOLF_DEBUG") else
                             logging.INFO)
    logger.addHandler(console_handler)
    logger.info(f'Logging to stdout and {logging_utils.DEFAULT_LOG_FILE}')
  else:
    logger.info(f'Logging to {logging_utils.DEFAULT_LOG_FILE}')


def RunTool() -> int:
  """
  Runs DFTimewolfTool.

  Returns:
    int: 0 DFTimewolf could be run successfully, 1 otherwise.
  """
  time_start = time.time()*1000
  tool = DFTimewolfTool()

  # TODO: log errors if this fails.
  tool.LoadConfiguration()
  logger.success(f'dfTimewolf tool initialized with UUID: {tool.uuid}')

  try:
    tool.ReadRecipes()
  except (KeyError, errors.RecipeParseError, errors.CriticalError) as exception:
    logger.critical(str(exception))
    return 1

  try:
    tool.ParseArguments(sys.argv[1:])
  except (errors.CommandLineParseError,
          errors.RecipeParseError,
          errors.CriticalError) as exception:
    logger.critical(str(exception))
    return 1

  try:
    tool.ValidateArguments(tool.dry_run)
  except errors.CriticalError as exception:
    logger.critical(str(exception))
    return 1

  tool.InterpolateArgs()
  tool.LogExecutionPlan()

  if tool.dry_run:
    logger.info("Exiting as --dry_run flag is set.")
    return 0

  tool.RunAllModules()

  tool.LogTelemetry()

  return 0


def Main() -> int:
  """Main function for DFTimewolf.

  Returns:
    int: 0 on success, 1 otherwise.
  """
  SetupLogging(stdout_log=True)
  return RunTool()


if __name__ == '__main__':
  signal.signal(signal.SIGINT, SignalHandler)
  sys.exit(Main())
