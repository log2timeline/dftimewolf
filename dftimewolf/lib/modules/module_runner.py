"""Handles running DFTW modules."""

import collections
import importlib
import logging
import sys
import threading
import time
import traceback
import typing
from concurrent import futures

from dftimewolf.lib import cache
from dftimewolf.lib import errors
from dftimewolf.lib import module as dftw_module
from dftimewolf.lib import telemetry
from dftimewolf.lib import utils
from dftimewolf.lib.containers import manager as container_manager
from dftimewolf.lib.modules import manager as modules_manager

# pylint: disable=line-too-long


NEW_ISSUE_URL = 'https://github.com/log2timeline/dftimewolf/issues/new'


class ModuleRunner(object):
  """Handles running DFTW modules."""

  def __init__(self,
               logger: logging.Logger,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: typing.Callable[[str, str, bool], None]) -> None:
    """Initialise the class."""
    self._recipe: dict[str, typing.Any] = {}
    self._module_pool: dict[str, dftw_module.BaseModule] = {}
    self._threading_event_per_module: dict[str, threading.Event] = {}

    self._errors: dict[str, list[errors.DFTimewolfError]] = collections.defaultdict(list)
    self._logger = logger

    self._container_manager = container_manager.ContainerManager(self._logger)
    self._telemetry = telemetry_
    self._publish_message_callback = publish_message_callback

    self._module_setup_args: dict[str, dict[str, typing.Any]] = {}

    self._cache = cache.DFTWCache()
    self._cache.SetCLIArgs(' '.join(sys.argv))

    self._messages: dict[str, list[str]] = collections.defaultdict(list)

  def PublishMessage(self, source: str, message: str, is_error: bool = False) -> None:
    """Wrapper for a passed in PublishMessage.

    Args:
      source: The source module of the message
      message: The message content
      is_error: True if the message is for an error, false otherwise.
    """
    self._messages[source].append(message)
    self._publish_message_callback(source, message, is_error)

  def Initialise(self, recipe_dict: dict[str, typing.Any], module_locations: dict[str, str]) -> None:
    """Based on a recipe and module mapping, load and instantiate required modules.

    Args:
      recipe_dict: A parsed and interpolated recipe dict.
      module_locations: A mapping of module names to package paths.
    """
    self._recipe = recipe_dict
    self._cache.SetRecipeName(self._recipe['name'])

    module_definitions = self._recipe.get('modules', [])
    preflight_definitions = self._recipe.get('preflights', [])
    self._ImportRecipeModules(module_locations)

    for module_definition in module_definitions + preflight_definitions:
      module_name = module_definition['name']
      runtime_name = module_definition.get('runtime_name')
      if not runtime_name:
        runtime_name = module_name
      module_class = modules_manager.ModulesManager.GetModuleByName(module_name)
      if module_class:
        self._module_pool[runtime_name] = module_class(name=runtime_name,
                                                       cache_=self._cache,
                                                       container_manager_=self._container_manager,
                                                       telemetry_=self._telemetry,
                                                       publish_message_callback=self.PublishMessage)
      else:
        raise RuntimeError(f'Could not instantiate module {module_name}')

    self._container_manager.ParseRecipe(self._recipe)
    self._cache.AddToCache('recipe_name', self._recipe['name'])

    modules = [
      module['name'] for module in self._recipe.get('modules', [])
    ]
    modules.extend([
      module['name'] for module in self._recipe.get('preflights', [])
    ])

    for module in sorted(modules):
      self._telemetry.LogTelemetry('module', module, 'core')

  def LogExecutionPlan(self) -> None:
    """Logs the result of FormatExecutionPlan() using the base logger."""
    for line in self._FormatExecutionPlan().split('\n'):
      self._logger.debug(line)

  def Run(self, running_args: dict[str, typing.Any]) -> int:
    """Runs the modules.

    Args:
      running_args: An already parsed and interpolated args object from the
          recipe parsing layer.

    Returns:
      Unix style - 1 on failure, 0 on success.
    """
    self._ExtractParsedSetUpArgs(running_args)

    time_ready = time.time()*1000
    self._SetUpAndRunPreflights()
    time_preflights = time.time()*1000
    self._telemetry.LogTelemetry(
      'preflights_delta', str(time_preflights - time_ready), 'core')

    # If a preflight has a critical error, bail out.
    for _, exceptions in self._errors.items():
      if any(e.critical for e in exceptions):
        self._logger.error('Halting execution due to preflight failure.')
        return 1

    try:
      self._SetupModules()

      time_setup = time.time()*1000
      self._telemetry.LogTelemetry('setup_delta', str(time_setup - time_preflights), 'core')

      self._RunModules()

      time_run = time.time()*1000
      self._telemetry.LogTelemetry('run_delta', str(time_run - time_setup), 'core')
    except errors.CriticalError as exception:
      self._logger.critical(str(exception))
      return 1
    finally:
      self._CleanUpPreflights()

    total_time = time.time()*1000 - time_ready
    self._telemetry.LogTelemetry('total_time', str(total_time), 'core')

    if self._errors:
      return 1
    return 0

  def GenerateReport(self) -> str:
    """Generates the runtime report from the module results and errors."""
    separator = '----------'

    lines = [self._recipe['name'], separator]

    for module, messages in self._messages.items():
      if not messages:
        continue
      lines.append(f'{module}:')
      lines.extend(f'  {message}' for message in messages)
      lines.append(separator)

    return '\n'.join(lines)

  def _ImportRecipeModules(self, module_locations: dict[str, str]) -> None:
    """Dynamically loads the modules declared in a recipe.

    Args:
      module_locations: A mapping of module names to package paths.

    Raises:
      errors.RecipeParseError: if a module requested in a recipe does not
          exist in the mapping.
    """
    for module in self._recipe.get('modules', []) + self._recipe.get('preflights', []):
      name = module['name']
      if name not in module_locations:
        msg = f'In {self._recipe["name"]}: module {name} cannot be found. It may not have been declared.'
        raise errors.RecipeParseError(msg)
      self._logger.debug('Loading module %s from %s', name, module_locations[name])

      location = module_locations[name]
      try:
        importlib.import_module(location)
      except ModuleNotFoundError as exception:
        msg = f'Cannot find Python module for {name} ({location}): {exception}'
        raise errors.RecipeParseError(msg)

  def _ExtractParsedSetUpArgs(self, running_args: dict[str, typing.Any]) -> None:
    """Given parsed running args, extract module set up args."""
    if 'preflights' not in self._recipe or 'modules' not in self._recipe:
      raise RuntimeError('Recipe is malformed.')

    for module_definition in (running_args.get('preflights', []) +
                              running_args.get('modules', [])):
      runtime_name = module_definition.get('runtime_name', module_definition['name'])
      self._module_setup_args[runtime_name] = module_definition.get('args', {})

  def _SetupModules(self) -> None:
    """Performs setup tasks for each module in the module pool.

    Threads declared modules' SetUp() functions. Takes CLI arguments into
    account when replacing recipe parameters for each module.
    """
    self._InvokeModulesInThreads(self._SetupModuleThreadCallback)

  def _RunModules(self) -> None:
    """Performs the actual processing for each module in the module pool."""
    self._InvokeModulesInThreads(self._RunModuleThreadCallback)

  def _InvokeModulesInThreads(self, callback: typing.Callable[[typing.Any], typing.Any]) -> None:
    """Invokes the callback function on all the modules in separate threads.

    Args:
      callback (function): callback function to invoke on all the modules.
    """
    threads: list[threading.Thread] = []
    for module_definition in self._recipe['modules']:
      thread_args = (module_definition,)
      thread = threading.Thread(target=callback, args=thread_args)
      thread.name = thread.name[:thread.name.find(' ')]
      threads.append(thread)
      thread.start()

    for thread in threads:
      thread.join()

  def _SetUpAndRunPreflights(self) -> None:
    """Run all preflight modules."""
    for preflight_definition in self._recipe.get('preflights', []):
      preflight_name = preflight_definition['name']
      runtime_name = preflight_definition.get('runtime_name', preflight_name)

      preflight = self._module_pool[runtime_name]

      try:
        preflight.SetUp(**(self._module_setup_args[runtime_name]))
        preflight.Process()
      except errors.DFTimewolfError as error:
        self._HandledException(error, runtime_name)
      except Exception as error:  # pylint: disable=broad-exception-caught
        self._UnhandledException(error, runtime_name)

      self._container_manager.CompleteModule(runtime_name)
      self._threading_event_per_module[runtime_name] = threading.Event()
      self._threading_event_per_module[runtime_name].set()

  def _SetupModuleThreadCallback(self, module_definition: dict[str, str]) -> None:
    """Calls the module's SetUp() function and sets a threading event for it.

    Callback for _InvokeModulesInThreads.

    Args:
      module_definition (dict[str, str]): recipe module definition.
    """
    module_name = module_definition['name']
    runtime_name = module_definition.get('runtime_name', module_name)
    self._logger.info('Setting up module: {0:s}'.format(runtime_name))

    module = self._module_pool[runtime_name]

    self._messages[runtime_name] = []

    try:
      if runtime_name in self._errors and any(e.critical for e in self._errors[runtime_name]):
        self._logger.warning('Aborting execution of %s due to previous critical error', runtime_name)
        return

      module.SetUp(**(self._module_setup_args[runtime_name]))
    except errors.DFTimewolfError as error:
      self._HandledException(error, runtime_name)
    except Exception as error:  # pylint: disable=broad-exception-caught
      self._UnhandledException(error, runtime_name)

    self._threading_event_per_module[runtime_name] = threading.Event()

  def _RunModuleProcessThreaded(self, module: dftw_module.ThreadAwareModule) -> list[futures.Future[None]]:
    """Runs Process of a single ThreadAwareModule module.

    Designed to be wrapped by an output handling subclass.

    Args:
      module: The module that will have Process(container) called in a threaded
          fashion.

    Returns:
      List of futures for the threads that were started.
    """
    containers = self._container_manager.GetContainers(
        requesting_module=module.name,
        container_class=module.GetThreadOnContainerType(),
        pop=not module.KeepThreadedContainersInState())

    self._logger.info(f'Running {len(containers)} threads, max {module.GetThreadPoolSize()} simultaneous for module {module.name}')

    future_results = []

    with futures.ThreadPoolExecutor(max_workers=module.GetThreadPoolSize()) as executor:
      for c in containers:
        self._logger.debug(f"Launching {module.name}.Process thread with {str(c)}")
        future_results.append(executor.submit(module.Process, c))
    return future_results

  def _RunModuleThreadCallback(self, module_definition: dict[str, str]) -> None:
    """Runs the module's Process() function.

    Callback for _InvokeModulesInThreads.

    Waits for any blockers to have finished before running Process(), then
    sets an Event flag declaring the module has completed.

    Args:
      module_definition (dict): module definition.
    """
    module_name = module_definition['name']
    runtime_name = module_definition.get('runtime_name', module_name)

    for dependency in module_definition['wants']:
      self._threading_event_per_module[dependency].wait()

    module = self._module_pool[runtime_name]

    if runtime_name in self._errors and any(e.critical for e in self._errors[runtime_name]):
      self._logger.warning('Aborting execution of %s due to previous critical error', runtime_name)
      self._threading_event_per_module[runtime_name].set()
      return

    self._logger.info('Running module: {0:s}'.format(runtime_name))
    time_start = time.time()

    try:
      if isinstance(module, dftw_module.ThreadAwareModule):
        module.PreProcess()
        futures_ = self._RunModuleProcessThreaded(module)
        module.PostProcess()
        self._HandleFuturesFromThreadedModule(futures_)
      else:
        module.Process()

      self._container_manager.CompleteModule(runtime_name)

    except errors.DFTimewolfError as error:
      self._HandledException(error, runtime_name)
    except Exception as error:  # pylint: disable=broad-exception-caught
      self._UnhandledException(error, runtime_name)

    self._threading_event_per_module[runtime_name].set()
    self._logger.info('Module {0:s} finished execution'.format(runtime_name))
    total_time = utils.CalculateRunTime(time_start)
    module.LogTelemetry({"total_time": str(total_time)})

  def _HandleFuturesFromThreadedModule(self, futures_: list[futures.Future[None]]) -> None:
    """Handles any futures raised by the async processing of a module.

    Args:
      futures_: A list of futures, returned by RunModuleProcessThreaded().
    """
    for fut in futures_:
      fut.result()

  def _CleanUpPreflights(self) -> None:
    """Executes any cleanup actions defined in preflight modules."""
    for preflight_definition in self._recipe.get('preflights', []):
      preflight_name = preflight_definition['name']
      runtime_name = preflight_definition.get('runtime_name', preflight_name)
      preflight = self._module_pool[runtime_name]
      preflight.CleanUp()

  def _FormatExecutionPlan(self) -> str:
    """Formats execution plan.

    Returns information about loaded modules and their corresponding arguments
    to stdout.

    Returns:
      str: String representation of loaded modules and their parameters.
    """
    plan = ""
    maxlen = 0

    modules = self._recipe.get('preflights', []) + self._recipe.get('modules', [])

    for module in modules:
      if not module['args']:
        continue
      spacing = len(max(module['args'].keys(), key=len))
      maxlen = maxlen if maxlen > spacing else spacing

    for module in modules:
      runtime_name = module.get('runtime_name')
      if runtime_name:
        plan += '{0:s} ({1:s}):\n'.format(runtime_name, module['name'])
      else:
        plan += '{0:s}:\n'.format(module['name'])

      if not module['args']:
        plan += '  *No params*\n'
      for key, value in module['args'].items():
        plan += '  {0:s}{1:s}\n'.format(key.ljust(maxlen + 3), repr(value))

    return plan

  def _HandledException(self, error: errors.DFTimewolfError, runtime_name: str) -> None:
    """Handles DFTimewolfError exceptions."""
    message = f'Error encountered: {str(error)}'
    self._logger.error(message)
    self.PublishMessage(source=runtime_name, message=message, is_error=True)
    self._logger.debug('', exc_info=True)
    self._errors[runtime_name].append(error)

  def _UnhandledException(self, error: Exception, runtime_name: str) -> None:
    """Handles an otherwise unhandled exception."""
    message = f'Unhandled critical exception encountered: {str(error)}'
    self._logger.error(message)
    self.PublishMessage(source=runtime_name, message=message, is_error=True)
    self._logger.debug('', exc_info=True)
    self._errors[runtime_name].append(errors.DFTimewolfError(
        message=message,
        name=runtime_name,
        stacktrace=traceback.format_exc(),
        critical=True,
        unexpected=True))
