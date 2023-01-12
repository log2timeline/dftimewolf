"""Generic error wrapper"""
from typing import Optional

class DFTimewolfError(Exception):
  """Class to represent a DFTimewolfError.

  Attributes:
    message (str): The error message.
    name (str): Name of the module that generated the error.
    stacktrace (Optional[str]): Stacktrace leading to the error.
    critical (Optional[bool]): Whether the error is critical or not. Critical
        errors interrupt the recipe execution flow.
    unexpected (Optional[bool]): Whether the error is unexpected.
  """

  def __init__(self,
               message: Optional[str]=None,
               name: Optional[str]=None,
               stacktrace: Optional[str]=None,
               critical: bool=False,
               unexpected: bool=False) -> None:
    """Initializes the DFTimewolfError with provided or default message."""
    super(DFTimewolfError, self).__init__(message)
    self.message = message or 'An error occurred.'
    self.name = name
    self.stacktrace = stacktrace
    self.critical = critical
    self.unexpected = unexpected


class BadConfigurationError(DFTimewolfError):
  """Error when an issue with the configuration is encountered."""


class RecipeParseError(DFTimewolfError):
  """Error when parsing a recipe."""


class CommandLineParseError(DFTimewolfError):
  """Error when parsing the command-line arguments."""


class CriticalError(DFTimewolfError):
  """Critical error that should abort the whole workflow."""


class RecipeArgsValidatorError(DFTimewolfError):
  """Fatal error in recipe argument validation."""
