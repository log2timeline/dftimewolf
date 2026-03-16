#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""dftimewolf main entrypoint."""

import argparse
import logging
import os
import signal
import sys
import typing
import uuid
from typing import Any, Optional, cast

from dftimewolf import config
from dftimewolf.lib import errors
from dftimewolf.lib import logging_utils
from dftimewolf.lib import resources
from dftimewolf.lib import telemetry
from dftimewolf.lib import utils
from dftimewolf.lib.modules import module_runner
from dftimewolf.lib.recipes import manager as recipes_manager
from dftimewolf.lib.validators import manager as validators_manager


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


logger = cast(logging_utils.WolfLogger, logging.getLogger('dftimewolf'))


class DFTimewolfTool(object):
  """DFTimewolf tool."""

  _DEFAULT_DATA_FILES_PATH = os.path.join(
      os.sep, 'usr', 'local', 'share', 'dftimewolf')

  def __init__(
      self,
      workflow_uuid: Optional[str] = None,
      telemetry_: Optional[telemetry.BaseTelemetry] = None) -> None:
    """Initializes a DFTimewolf tool."""
    super().__init__()

    self._dry_run = False
    self._data_files_path = ''
    self._running_args: dict[str, typing.Any] = {}
    self._recipes_manager = recipes_manager.RecipesManager()
    self._recipe: resources.Recipe = None  # type: ignore
    self._uuid = workflow_uuid or str(uuid.uuid4())
    self._telemetry = telemetry_ or telemetry.GetTelemetry(uuid=self._uuid)
    self._module_runner = module_runner.ModuleRunner(logger, self._telemetry, self.PublishMessage)

    logger.success(f'dfTimewolf tool initialized with UUID: {self._uuid}')

    self._DetermineDataFilesPath()

  @property
  def dry_run(self) -> bool:
    """Whether we should just be testing parameters, or full execution."""
    return self._dry_run

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

  def GenerateHelpText(self) -> str:
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
        short_description = recipe.contents.get('short_description', 'No description')
        help_text += ' {0:<35s}{1:s}\n'.format(recipe.name, short_description)

    return help_text

  def LoadConfiguration(self, additional_path: str | None = None) -> None:
    """Loads config DFTW config files.

    The following paths are tried. Values loaded last take precedence.

    * <_data_files_path>/config.json
    * /etc/dftimewolf.conf
    * /usr/share/dftimewolf/dftimewolf.conf
    * ~/.dftimewolfrc
    * If set, additional_path arg
    * If set, wherever the DFTIMEWOLF_CONFIG environment variable points to

    Args:
      additional_path: An optional extra filepath to load config from.
    """
    paths = [
        os.path.join(self._data_files_path, 'config.json'),
        os.path.join('/', 'etc', 'dftimewolf.conf'),
        os.path.join('/', 'usr', 'share', 'dftimewolf', 'dftimewolf.conf'),
        os.path.join(os.path.expanduser('~'), '.dftimewolfrc')
    ]

    if additional_path:
      paths.append(additional_path)
    if os.environ.get('DFTIMEWOLF_CONFIG'):
      paths.append(os.environ['DFTIMEWOLF_CONFIG'])

    for path in paths:
      self._LoadConfigurationFromFile(path)

  def ReadRecipes(self, additional_directories: list[str] | None = None) -> None:
    """Reads recipes from the default directory, and any additional paths.

    Args:
      additional_directories: A list of directory paths to load recipes from.
    """
    directories = [os.path.join(self._data_files_path, 'recipes')]
    if additional_directories:
      directories.extend(additional_directories)

    for directory in directories:
      self._recipes_manager.ReadRecipesFromDirectory(directory)

    if not self._recipes_manager.Recipes():
      raise RuntimeError('No recipes loaded.')

  def SelectRecipe(self, recipe_name: str) -> None:
    """Selects a recipe for usage.

    Args:
      recipe_name: The name of the recipe to use.
    """
    self._recipe = self._recipes_manager.GetRecipe(recipe_name)
    self._module_runner.Initialise(self._recipe.contents, MODULES)

    # At this point we no longer need the recipe manager
    del self._recipes_manager

  def GenerateArgsParserForRecipe(self) -> argparse.ArgumentParser:
    """Generate an args parsing object that can be used to parse sys.argv[x:y].

    Used for a recipe to be able to take parameters from the command line.

    Returns:
      An args parsing object that can be used to parse command line options.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry_run', help='Tool dry run', default=False, action='store_true')

    for arg in self._recipe.args:
      action = argparse.BooleanOptionalAction if isinstance(arg.default, bool) else 'store'
      parser.add_argument(arg.switch, help=arg.help_text, default=arg.default, action=action)

    parser.set_defaults(**config.Config.GetExtra())

    return parser

  def GetRecipeDefaults(self) -> dict[str, Any]:
    """Collects recipe argument defaults."""
    return {arg.switch.replace('--', ''): arg.default for arg in self._recipe.args}

  def ApplyArgs(self, params: dict[str, Any]) -> None:
    """Validates and applies parameters to interpolate into a recipe.

    Args:
      params: A dict of arg name to value

    Raises:
      errors.CriticalError: If one or more arguments could not be validated.
    """
    self._running_args = params
    self._dry_run = self._running_args.get('dry_run', False)

    # Validate the args first
    self._ValidateArguments(self._dry_run)

    # Then interpolate them into the recipe
    self._InterpolateArgs()

  def RunAllModules(self) -> int:
    """Runs the modules.

    Returns:
      Unix style - 1 on error, 0 on success.
    """
    logger.info('Running modules...')

    return_value = self._module_runner.Run(self._recipe.contents)
    if not return_value:
      logger.info('Modules run successfully!')
    return return_value

  def LogTelemetry(self) -> None:
    """Prints collected telemetry if existing."""

    for line in self._telemetry.FormatTelemetry().split('\n'):
      logger.debug(line)

  def LogExecutionPlan(self) -> None:
    """log the execution plan."""
    self._module_runner.LogExecutionPlan()

  def AddLoggingHandler(self, handler: logging.Handler) -> None:
    """Adds an additional logging handler."""
    if handler not in logger.handlers:
      logger.addHandler(handler)
    self._module_runner.AddLoggingHandler(handler)

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

  def _ValidateArguments(self, dry_run: bool=False) -> None:
    """Validate the arguments.

    Args:
      dry_run: True if the tool is only testing parameters, False otherwise.

    Raises:
      errors.CriticalError: If one or more arguments could not be validated.
    """
    error_messages = []

    for arg in self._recipe.args:
      expanded_argument = self._SubstituteValidationParameters(arg)

      switch = expanded_argument.switch.replace('--', '')
      argument_mandatory = switch == arg.switch
      argument_value = self._running_args.get(switch)

      if argument_mandatory or argument_value is not None:
        try:
          valid_value = validators_manager.ValidatorsManager.Validate(argument_value, arg, dry_run)
          self._running_args[switch] = valid_value
        except errors.RecipeArgsValidationFailure as exception:
          error_messages.append(f'Invalid argument: "{arg.switch}" with value "{argument_value}". Error: {str(exception)}')
        except errors.RecipeArgsValidatorError as exception:
          error_messages.append(f'Argument validation error: "{arg.switch}" with value "{argument_value}". Error: {str(exception)}')

    if error_messages:
      for message in error_messages:
        logger.critical(message)
      raise errors.CriticalError('At least one argument failed validation')

  def _InterpolateArgs(self) -> None:
    """Interpolate config values and CLI args into the recipe args."""
    for module in (self._recipe.contents.get('preflights', []) +
                   self._recipe.contents.get('modules', [])):
      module['args'] = utils.ImportArgsFromDict(module['args'],
                                                self._running_args,
                                                config.Config)

  def _SubstituteValidationParameters(self, arg: resources.RecipeArgument) -> resources.RecipeArgument:
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

  def GetReport(self) -> str:
    """Fetches the runtime report from the module runner."""
    return f'\n{self._module_runner.GenerateReport()}'


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
  """Runs DFTimewolfTool.

  Returns:
    int: 0 DFTimewolf could be run successfully, 1 otherwise.
  """
  tool = DFTimewolfTool()

  try:
    tool.LoadConfiguration()
    tool.ReadRecipes()

    help_requested = any(h in sys.argv for h in ('-h', '--help'))

    if len(sys.argv) < 2 or help_requested:
      print(tool.GenerateHelpText(), file=sys.stderr)
      return not help_requested

    tool.SelectRecipe(sys.argv[1])
    args_parser = tool.GenerateArgsParserForRecipe()
    params = vars(args_parser.parse_args(sys.argv[2:]))

    tool.ApplyArgs(params)
  except recipes_manager.RecipeNotFoundError as error:
    logger.error(str(error))
    print(tool.GenerateHelpText(), file=sys.stderr)
    return 1
  except Exception as error:  # pylint: disable=broad-except
    logger.critical(str(error))
    logger.debug('', exc_info=True)
    return 1

  if tool.dry_run:
    logger.info("Exiting as --dry_run flag is set.")
    return 0

  tool.LogExecutionPlan()

  return_value = tool.RunAllModules()

  tool.LogTelemetry()

  print(tool.GetReport())

  return return_value


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
