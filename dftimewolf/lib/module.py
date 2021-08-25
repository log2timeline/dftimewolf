# -*- coding: utf-8 -*-
"""Class definition for DFTimewolf modules."""

import abc
import logging
# Some AttributeErrors occurred when trying to access logging.handlers, so
# we import them separately
from logging import handlers
import threading
import traceback
import sys

from copy import deepcopy

from typing import Optional, TYPE_CHECKING, Type, cast, TypeVar, Sequence, \
    List, Dict, Any

from dftimewolf.lib import errors
from dftimewolf.lib import logging_utils
from dftimewolf.lib.containers import interface

if TYPE_CHECKING:
  # Import will only happen during type checking, disabling linter warning.
  from dftimewolf.lib import state  # pylint: disable=cyclic-import
T = TypeVar("T", bound="interface.AttributeContainer")  # pylint: disable=invalid-name,line-too-long


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
               state: "state.DFTimewolfState",
               name:Optional[str]=None,
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

    # If more class attributes are added here, add them to the exclusion list
    # in ThreadAwareModule.__deepcopy__()

    self.SetupLogging()

  def SetupLogging(self) -> None:
    """Sets up stream and file logging for a specific module."""
    self.logger.setLevel(logging.DEBUG)

    file_handler = handlers.RotatingFileHandler(
        logging_utils.DEFAULT_LOG_FILE,
        maxBytes=logging_utils.MAX_BYTES,
        backupCount=logging_utils.BACKUP_COUNT)
    file_handler.setFormatter(logging_utils.WolfFormatter(colorize=False))
    self.logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    formatter = logging_utils.WolfFormatter(random_color=True)
    console_handler.setFormatter(formatter)

    self.logger.addHandler(console_handler)

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

    error = errors.DFTimewolfError(
        message, name=self.name, stacktrace=stacktrace, critical=critical)
    self.state.AddError(error)
    if critical:
      self.logger.critical(error.message)
      raise error
    self.logger.error(error.message)

  @abc.abstractmethod
  def Process(self) -> None:
    """Processes input and builds the module's output attribute.

    Modules take input information and process it into output information,
    which can in turn be ingested as input information by other modules.
    """

  @abc.abstractmethod
  def SetUp(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """Sets up necessary module configuration options."""

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

  ThreadAwareModule are modules designed to to better handle being run in
  parallel.

  How to implement this class:

  * This module will be threaded based on a nominated ThreadOn container type:
  so nominated by returning the class type in GetThreadOnContainerType().

  * There are a number of static methods that you can use to run once,
  regardless of the number of threads that will run.

  * SetUp will run once.

  * Process will run N times in parallel threads - N is the number of
  containers of the nominated type generated by previous modules. Process
  will be able to access only one container of the type specified by
  GetThreadOnContainerType(), and all other containers.

  * Access containers using self.[Get|Store]Container(). This differs from
  unthreaded modules which use self.state.[Get|Store]Container().

  * Copies of modules will not persist changes to any class attributes across
  parallel runs of Process. This is only relevant to StaticPostProcess, which
  therefore will not see changes made to class attributes in Process.
  """

  def __init__(self,
               state: "state.DFTimewolfState",
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a ThreadAwareModule.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(ThreadAwareModule, self).__init__(
        state, name=name, critical=critical)
    self._thread_lock = threading.Lock()
    self.store = {}  # type: Dict[str, List[interface.AttributeContainer]]

  def __deepcopy__(self, memo: Dict[Any, Any]) -> object:
    """Override of deepcopy. We cheat a little - The container to thread on is
    deepcopy'd, but other containers are shallow copied - so all instances of
    the module can access and modify them by reference"""
    state = deepcopy(self.state, memo)
    copy = ThreadAwareModule(state) # type: ignore
    copy._thread_lock = threading.Lock()
    copy.__class__ = type(self)

    # Deep copy the containers to thread on, shallow copy the rest.
    for key, container_list in self.store.items():
      if key == self.GetThreadOnContainerType().CONTAINER_TYPE:
        copy.store[key] = deepcopy(container_list)
      else:
        copy.store[key] = container_list

    # Copy any class attributes that a subclass may create
    for key, value in self.__dict__.items():
      if key not in \
          ['name', 'critical', 'state', 'logger', '_thread_lock', 'store']:
        copy.__dict__[key] = value

    return copy

  @staticmethod
  @abc.abstractmethod
  def StaticPreSetUp() -> None:
    """Carries out optional SetUp actions that only need to be performed once,
    regardless of the number of class instantiations. Called before SetUp."""

  @staticmethod
  @abc.abstractmethod
  def StaticPostSetUp() -> None:
    """Carries out optional SetUp actions that only need to be performed once,
    regardless of the number of class instantiations. Called after SetUp."""

  @staticmethod
  @abc.abstractmethod
  def StaticPreProcess() -> None:
    """Carries out optional Process actions that only need to be performed
    once, regardless of the number of class instantiations. Called before
    Process."""

  @staticmethod
  @abc.abstractmethod
  def StaticPostProcess() -> None:
    """Carries out optional Process actions that only need to be performed
    once, regardless of the number of class instantiations. Called after
    Process."""

  @staticmethod
  @abc.abstractmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    """Returns the container type that this module should be threaded on."""

  @staticmethod
  @abc.abstractmethod
  def GetThreadPoolSize() -> int:
    """Returns the maximum number of threads for this module."""

  # The following two methods are copy/pasted from dftimewolf/lib/state.py
  # to better handle a move to parallel threading of modules. Any instance of
  # this module should use these methods to access containers, rather than
  # the same methods in the state.
  def StoreContainer(self, container: "interface.AttributeContainer") -> None:
    """Thread-safe method to store data in the state's store.

    Args:
      container (AttributeContainer): data to store.
    """
    with self._thread_lock:
      self.store.setdefault(container.CONTAINER_TYPE, []).append(container)

  def GetContainers(self,
                    container_class: Type[T],
                    pop: bool=False) -> Sequence[T]:
    """Thread-safe method to retrieve data from the state's store.

    Args:
      container_class (type): AttributeContainer class used to filter data.
      pop (Optional[bool]): Whether to remove the containers from the state when
          they are retrieved.

    Returns:
      Collection[AttributeContainer]: attribute container objects provided in
          the store that correspond to the container type.
    """
    with self._thread_lock:
      container_objects = cast(
          List[T], self.store.get(container_class.CONTAINER_TYPE, []))
      if pop:
        self.store[container_class.CONTAINER_TYPE] = []
      return tuple(container_objects)
