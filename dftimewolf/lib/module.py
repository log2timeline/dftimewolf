# -*- coding: utf-8 -*-
"""Class definition for DFTimewolf modules."""
# pytype: disable=ignored-abstractmethod,bad-return-type

import abc
import logging
# Some AttributeErrors occurred when trying to access logging.handlers, so
# we import them separately
from logging import handlers
import os
import traceback
import threading
import sys

from typing import Optional, Type, cast, TypeVar, Dict, Any, Sequence, Callable
from typing import TYPE_CHECKING

from dftimewolf.lib import errors
from dftimewolf.lib import logging_utils
from dftimewolf.lib import telemetry
from dftimewolf.lib.containers import interface

if TYPE_CHECKING:
  from dftimewolf.lib import state as state_lib  # pylint: disable=cyclic-import

T = TypeVar("T", bound="interface.AttributeContainer")  # pylint: disable=invalid-name,line-too-long

TELEMETRY = telemetry

class BaseModule(object):
  """Interface of a DFTimewolf module.

  Attributes:
    critical (bool): True if this module is critical to the execution of
        the recipe. If set to True, and the module fails to properly run,
        the recipe will be aborted.
    name (str): A unique name for a specific instance of the module
          class. If not provided, will default to the module's class name.
    state (DFTimewolfState): recipe state.
  """

  def __init__(self,
               state: "state_lib.DFTimewolfState",
               name: Optional[str]=None,
               critical: Optional[bool]=False):
    """Initialize a module.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): A unique name for a specific instance of the module
          class. If not provided, will default to the module's class name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(BaseModule, self).__init__()
    self.name = name if name else self.__class__.__name__
    self.critical = critical
    self.state = state
    self.logger = cast(logging_utils.WolfLogger,
                       logging.getLogger(name=self.name))
    self.logger.propagate = False
    self.SetupLogging()

  def SetupLogging(self, threaded: bool = False) -> None:
    """Sets up stream and file logging for a specific module."""
    debug = bool(os.environ.get("DFTIMEWOLF_DEBUG"))
    if debug:
      self.logger.setLevel(logging.DEBUG)
    else:
      self.logger.setLevel(logging.INFO)

    file_handler = handlers.RotatingFileHandler(logging_utils.DEFAULT_LOG_FILE)
    file_handler.setFormatter(logging_utils.WolfFormatter(
        colorize=False,
        threaded=threaded))
    file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
    self.logger.addHandler(file_handler)

    if self.state.stdout_log:
      console_handler = logging.StreamHandler(stream=sys.stdout)
      formatter = logging_utils.WolfFormatter(
          random_color=True)
      console_handler.setFormatter(formatter)

      self.logger.addHandler(console_handler)

  def LogTelemetry(self, data: Dict[str, str]) -> None:
    """Logs useful telemetry using the telemetry attribute in the state object.

    Args:
      data: Key-value telemetry to store.

    Raises:
      ValueError: If the keys in the telemetry dict are not strings.
    """
    if not all (isinstance(key, str) for key in data.keys()):
      raise ValueError("telemetry keys must be strings.")
    if not all (isinstance(value, str) for value in data.values()):
      raise ValueError("telemetry values must be strings.")
    entry = telemetry.TelemetryCollection(
        type(self).__name__,
        self.name,
        self.state.recipe.get('name', 'N/A'),
        data,
    )
    self.state.LogTelemetry(entry)

  def CleanUp(self) -> None:
    """Cleans up module output to prepare it for the next module."""
    # No clean up is required.
    return

  def ModuleError(self, message: str, critical: bool=False) -> None:
    """Declares a module error.

    Errors will be stored in a DFTimewolfError error object and passed on to the
    state. Critical errors will also raise a DFTimewolfError error.

    Args:
      message (str): Error text.
      critical (Optional[bool]): True if dfTimewolf cannot recover from
          the error and should abort execution.

    Raises:
      errors.DFTimewolfError: If the error is critical and dfTimewolf
          should abort execution of the recipe.
    """
    stacktrace = None
    if sys.exc_info() != (None, None, None):
      stacktrace = traceback.format_exc()
      if self.state.telemetry:
        self.state.telemetry.LogTelemetry(
          'error_stacktrace', stacktrace, self.name,
          self.state.recipe.get('name', 'N/A')
        )

    error = errors.DFTimewolfError(
        message, name=self.name, stacktrace=stacktrace, critical=critical)
    if self.state.telemetry:
      recipe_name = self.state.recipe.get('name', 'N/A')
      self.state.telemetry.LogTelemetry(
          'error_detail',message, self.name, recipe_name
      )

    self.state.AddError(error)
    self.PublishMessage(message, is_error=True, is_critical=critical)
    if critical:
      raise error

  def PublishMessage(
      self, message: str, is_error: bool = False, is_critical: bool = False
  ) -> None:
    """Logs a message, and sends the message to the state.

    Args:
      message: The message content.
      is_error: True if the message is an error message, False otherwise.
      is_critical: True if the message is a critical error.
    """
    if is_critical:
      self.logger.critical(message)
    elif is_error:
      self.logger.error(message)
    else:
      self.logger.success(message)
    self.state.PublishMessage(self.name, message, is_error)

  def RegisterStreamingCallback(self,
                                container_type: T,
                                callback: Callable[[T], None]) -> None:
    """Registers a streaming callback with the state for this module."""
    self.state.RegisterStreamingCallback(
        module_name=self.name,
        callback=callback,
        container_type=container_type)

  def StoreContainer(self, container: "interface.AttributeContainer") -> None:
    """Stores a container in the state's container store.

    Args:
      container (AttributeContainer): data to store.
    """
    self.state.StoreContainer(container, self.name)

  def GetContainers(self,
                    container_class: Type[T],
                    pop: bool=False,
                    metadata_filter_key: Optional[str]=None,
                    metadata_filter_value: Optional[Any]=None) -> Sequence[T]:
    """Retrieve containers from the state container store.

    Args:
      container_class (type): AttributeContainer class used to filter data.
      pop (Optional[bool]): Whether to remove the containers from the state when
          they are retrieved.
      metadata_filter_key (Optional[str]): Metadata key to filter on.
      metadata_filter_value (Optional[Any]): Metadata value to filter on.

    Returns:
      Collection[AttributeContainer]: attribute container objects provided in
          the store that correspond to the container type.

    Raises:
      RuntimeError: If only one metadata filter parameter is specified.
    """
    return self.state.GetContainers(self.name,
                                    container_class,
                                    pop,
                                    metadata_filter_key,
                                    metadata_filter_value)

  @abc.abstractmethod
  def Process(self) -> None:
    """Processes input and builds the module's output attribute.

    Modules take input information and process it into output information,
    which can in turn be ingested as input information by other modules.
    """

  @abc.abstractmethod
  def SetUp(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """Sets up necessary module configuration options."""

  def ProgressUpdate(self, steps_taken: int, steps_expected: int) -> None:
    """Send an update to the state on progress."""
    self.state.ProgressUpdate(
        self.name, steps_taken, steps_expected)


class PreflightModule(BaseModule):
  """Base class for preflight modules.

  Preflight modules are special modules that are executed synchronously before
  other modules. They are intended for modules that primarily retrieve
  attributes for other modules in a recipe, for example from a ticketing system.
  """

  @abc.abstractmethod
  def Process(self) -> None:
    """Processes input and builds the module's output attribute.

    Modules take input information and process it into output information,
    which can in turn be ingested as input information by other modules.
    """

  @abc.abstractmethod
  def SetUp(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """Sets up necessary module configuration options."""

  @abc.abstractmethod
  def CleanUp(self) -> None:
    """Carries out optional cleanup actions at the end of the recipe run."""

class ThreadAwareModule(BaseModule):
  """Base class for ThreadAwareModules.

  ThreadAwareModule are modules designed to handle being run in parallel.

  How to implement this class:

  * This module will be threaded based on a nominated ThreadOn container type:
  so nominated by returning the class type in GetThreadOnContainerType().

  * There are a number of static methods that you can use to run once,
  regardless of the number of threads that will run.

  * SetUp will run once.

  * Process will run N times in GetThreadPoolSize() parallel threads - N is the
  number of containers of the nominated type generated by previous modules.
  Process will be passed one container of the type specified by
  GetThreadOnContainerType().
  """

  def __init__(self,
               state: "state_lib.DFTimewolfState",
               name: Optional[str]=None,
               critical: Optional[bool]=False) -> None:
    """Initializes a ThreadAwareModule.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(ThreadAwareModule, self).__init__(
        state, name=name, critical=critical)

    # The call to super.__init__ sets up the logger, but we want to change it
    # for threaded modules.
    self.logger.handlers.clear()
    self.SetupLogging(threaded=True)

  @abc.abstractmethod
  def PreProcess(self) -> None:
    """Carries out optional Process actions that only need to be performed
    once, regardless of the number of class instantiations. Called before
    Process."""

  # pylint: disable=arguments-differ
  @abc.abstractmethod
  def Process(self, container: interface.AttributeContainer
              ) -> None:  # pytype: disable=signature-mismatch
    """Carry out a single process based on the input container. This will be
    run in parallel, based on the number of containers of the ThreadOn type,
    given by GetThreadOnContainerType(), up to GetThreadPoolSize() max
    simultaneous threads."""
  # pylint: enable=arguments-differ

  @abc.abstractmethod
  def PostProcess(self) -> None:
    """Carries out optional Process actions that only need to be performed
    once, regardless of the number of class instantiations. Called after
    Process."""

  @abc.abstractmethod
  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    """Returns the container type that this module should be threaded on."""

  @abc.abstractmethod
  def GetThreadPoolSize(self) -> int:
    """Returns the maximum number of threads for this module."""

  def KeepThreadedContainersInState(self) -> bool:
    """Whether to keep the containers that are used to thread on in the state,
    or pop them. Default behaviour is to keep the containers. Override this
    method to return false to pop them from the state."""
    return True

  def ThreadProgressUpdate(self, steps_taken: int, steps_expected: int) -> None:
    """Send an update to the state on progress."""
    thread_id = threading.current_thread().name
    self.state.ThreadProgressUpdate(
        self.name, thread_id, steps_taken, steps_expected)
