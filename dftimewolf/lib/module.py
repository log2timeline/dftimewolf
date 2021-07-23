# -*- coding: utf-8 -*-
"""Class definition for DFTimewolf modules."""

import abc
import logging
# Some AttributeErrors occurred when trying to access logging.handlers, so
# we import them separately
from logging import handlers
import traceback
import sys

from typing import Optional, TYPE_CHECKING

from dftimewolf.lib import errors
from dftimewolf.lib import logging_utils

if TYPE_CHECKING:
  # Import will only happen during type checking, disabling linter warning.
  from dftimewolf.lib import state  # pylint: disable=cyclic-import


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
    self.SetupLogging()

  def SetupLogging(self) -> None:
    """Sets up stream and file logging for a specific module."""
    self.logger = logging.getLogger(name=self.name)
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
