from dftimewolf.lib import cache
from dftimewolf.lib import errors
from dftimewolf.lib import module as dftw_module
from dftimewolf.lib.containers import manager as container_manager
from dftimewolf.lib import telemetry
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import utils

import importlib
from concurrent import futures
import logging
import threading
import time
import traceback
import typing

# pylint: disable=line-too-long


class ModuleRunner(object):
  """Handles running DFTW modules."""

  def __init__(self,
               logger: logging.Logger,
               telemetry: telemetry.BaseTelemetry,
               publish_message_callback: typing.Callable[[str, str, bool], None]) -> None:
    """Initialise the class."""



    self._logger = logger
    self._recipe: dict[str, typing.Any] = {}
    self._running_args: dict[str, typing.Any] = {}
    self._abort_execution = False


    self._module_pool: dict[str, dftw_module.BaseModule] = {}
    self._threading_event_per_module: dict[str, threading.Event] = {}

    self._cache = cache.DFTWCache()
    self._container_manager = container_manager.ContainerManager(self._logger)
    self._telemetry = telemetry
    self._publish_message_callback = publish_message_callback


  def LoadModules(self, recipe: dict[str, typing.Any], module_locations: dict[str, str]) -> None:
    """Based on a recipe and module mapping, load and instantiate required modules.
    
    
    """
    self._recipe = recipe

    module_definitions = self._recipe.get('modules', [])
    preflight_definitions = self._recipe.get('preflights', [])
    self._ImportRecipeModules(recipe, module_locations)

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
                                                       publish_message_callback=self._publish_message_callback)

    self._container_manager.ParseRecipe(self._recipe)
    self._cache.AddToCache('recipe_name', recipe['name'])

  def Run(self, running_args: dict[str, typing.Any]) -> int:
    """Runs the modules."""
    self._running_args = running_args

    time_ready = time.time()*1000
    self._SetUpAndRunPreflights()
    time_preflights = time.time()*1000
    self._telemetry.LogTelemetry(
      'preflights_delta', str(time_preflights - time_ready), 'core')

    try:
      self._SetupModules()
    except errors.CriticalError as exception:
      self._logger.critical(str(exception))
      return 1

    time_setup = time.time()*1000
    self._telemetry.LogTelemetry(
      'setup_delta', str(time_setup - time_preflights), 'core')

    try:
      self._RunModules()
    except errors.CriticalError as exception:
      self._logger.critical(str(exception))
      return 1
    finally:
      time_run = time.time()*1000
      self._telemetry.LogTelemetry(
        'run_delta', str(time_run - time_setup), 'core')

      self._CleanUpPreflights()

    return 0



  def _ImportRecipeModules(self, recipe: dict[str, typing.Any], module_locations: dict[str, str]) -> None:
    """Dynamically loads the modules declared in a recipe.

    Args:

    Raises:
      errors.RecipeParseError: if a module requested in a recipe does not
          exist in the mapping.
    """
    for module in recipe['modules'] + recipe.get('preflights', []):
      name = module['name']
      if name not in module_locations:
        msg = f'In {recipe["name"]}: module {name} cannot be found. It may not have been declared.'
        raise errors.RecipeParseError(msg)
      self._logger.debug('Loading module %s from %s', name, module_locations[name])

      location = module_locations[name]
      try:
        importlib.import_module(location)
      except ModuleNotFoundError as exception:
        msg = f'Cannot find Python module for {name} ({location}): {exception}'
        raise errors.RecipeParseError(msg)
      
  def _SetupModules(self) -> None:
    """Performs setup tasks for each module in the module pool.

    Threads declared modules' SetUp() functions. Takes CLI arguments into
    account when replacing recipe parameters for each module.
    """
    self._InvokeModulesInThreads(self._SetupModuleThread)

  def _RunModules(self) -> None:
    """Performs the actual processing for each module in the module pool."""
    self._InvokeModulesInThreads(self._RunModuleThread)

  def _InvokeModulesInThreads(self, callback: typing.Callable[[typing.Any], typing.Any]) -> None:
    """Invokes the callback function on all the modules in separate threads.

    Args:
      callback (function): callback function to invoke on all the modules.
    """
    threads = []
    for module_definition in self._recipe['modules']:
      thread_args = (module_definition,)
      thread = threading.Thread(target=callback, args=thread_args)
      threads.append(thread)
      thread.start()

    for thread in threads:
      thread.join()

#    self.CheckErrors(is_global=True)

  def _SetUpAndRunPreflights(self) -> None:
    """Run all preflight modules."""
    for preflight_definition in self._recipe.get('preflights', []):
      preflight_name = preflight_definition['name']
      runtime_name = preflight_definition.get('runtime_name', preflight_name)

      args = preflight_definition.get('args', {})

      new_args = utils.ImportArgsFromDict(args, self._running_args)
      preflight = self._module_pool[runtime_name]
      try:
        preflight.SetUp(**new_args)
        preflight.Process()
        self._container_manager.CompleteModule(runtime_name)
        self._threading_event_per_module[runtime_name] = threading.Event()
        self._threading_event_per_module[runtime_name].set()
      finally:
        pass
        # self.CheckErrors(is_global=True)

  def _SetupModuleThread(self, module_definition: dict[str, str]) -> None:
    """Calls the module's SetUp() function and sets a threading event for it.

    Callback for _InvokeModulesInThreads.

    Args:
      module_definition (dict[str, str]): recipe module definition.
    """
    module_name = module_definition['name']
    runtime_name = module_definition.get('runtime_name', module_name)
    self._logger.info('Setting up module: {0:s}'.format(runtime_name))

    setup_args = utils.ImportArgsFromDict(module_definition['args'], self._running_args)
    module = self._module_pool[runtime_name]

    try:
      module.SetUp(**setup_args)
    except errors.DFTimewolfError:
      msg = "A critical error occurred in module {0:s}, aborting execution."
      self._logger.critical(msg.format(module.name))
    except Exception as exception:  # pylint: disable=broad-except
      msg = 'An unknown error occurred in module {0:s}: {1!s}'.format(
          module.name, exception)
      self._logger.critical(msg)
      # We're catching any exception that is not a DFTimewolfError, so we want
      # to generate an error for further reporting.
      error = errors.DFTimewolfError(
          message=msg,
          name='dftimewolf',
          stacktrace=traceback.format_exc(),
          critical=True,
          unexpected=True)
#      self.AddError(error)
      self._abort_execution = True

    self._threading_event_per_module[runtime_name] = threading.Event()
#    self.CleanUp()

  def _RunModuleProcessThreaded(self, module: dftw_module.ThreadAwareModule) -> list[futures.Future]:
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

  def _RunModuleThread(self, module_definition: dict[str, str]) -> None:
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

    # Abort processing if a module has had critical failures before.
    if self._abort_execution:
      self._logger.critical(
          'Aborting execution of {0:s} due to previous errors'.format(
              module.name))
      self._threading_event_per_module[runtime_name].set()
#      self.CleanUp()
      return

    self._logger.info('Running module: {0:s}'.format(runtime_name))
    time_start = time.time()

    try:
      if isinstance(module, dftw_module.ThreadAwareModule):
        module.PreProcess()
        futures = self._RunModuleProcessThreaded(module)
        module.PostProcess()
        self._HandleFuturesFromThreadedModule(futures, runtime_name)
      else:
        module.Process()
    except errors.DFTimewolfError:
      self._logger.critical(
          "Critical error in module {0:s}, aborting execution".format(
              module.name))
      self._abort_execution = True
    except Exception as exception:  # pylint: disable=broad-except
      self._abort_execution = True
      msg = 'An unknown error occurred in module {0:s}: {1!s}'.format(
          module.name, exception)
      self._logger.critical(msg)
      # We're catching any exception that is not a DFTimewolfError, so we want
      # to generate an error for further reporting.
      error = errors.DFTimewolfError(
          message=msg,
          name='dftimewolf',
          stacktrace=traceback.format_exc(),
          critical=True,
          unexpected=True)
#      self.AddError(error)

    self._logger.info('Module {0:s} finished execution'.format(runtime_name))
    total_time = utils.CalculateRunTime(time_start)
    module.LogTelemetry({"total_time": str(total_time)})
    self._threading_event_per_module[runtime_name].set()

    try:
      self._container_manager.CompleteModule(runtime_name)
    except Exception:  # pylint: disable=broad-exception-caught
      self._logger.warning('Unknown exception encountered', exc_info=True)

  def _HandleFuturesFromThreadedModule(
      self,
      futures: list[futures.Future],
      runtime_name: str) -> None:
    """Handles any futures raised by the async processing of a module.

    Args:
      futures: A list of futures, returned by RunModuleProcessThreaded().
      runtime_name: runtime name of the module."""
    for fut in futures:
      if fut.exception():
        raise fut.exception()

  def _CleanUpPreflights(self) -> None:
    """Executes any cleanup actions defined in preflight modules."""
    for preflight_definition in self._recipe.get('preflights', []):
      preflight_name = preflight_definition['name']
      runtime_name = preflight_definition.get('runtime_name', preflight_name)
      preflight = self._module_pool[runtime_name]
      try:
        preflight.CleanUp()
      finally:
        pass
#        self.CheckErrors(is_global=True)
