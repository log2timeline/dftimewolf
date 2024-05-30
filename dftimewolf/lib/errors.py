"""Generic error wrapper"""
from typing import Optional

class DFTimewolfError(Exception):
  """Class to represent a DFTimewolfError.

  Attributes:
    message: The error message.
    name: Name of the module that generated the error.
    stacktrace: Stacktrace leading to the error.
    critical: Whether the error is critical or not. Critical
        errors interrupt the recipe execution flow.
    unexpected: Whether the error is unexpected.
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

class RecipeArgsValidationFailure(DFTimewolfError):
  """Error that indicates a recipe argument is invalid.

  Attributes:
    switch: The name of the argument that is invalid.
    argument_value: The value of the argument that is invalid.
    description: Description of why the argument is invalid.
    message: The error message.
    name: Name of the module that generated the error.
    stacktrace: Stacktrace leading to the error.
    critical: Whether the error is critical or not. Critical
        errors interrupt the recipe execution flow.
    unexpected: Whether the error is unexpected.
  """

  def __init__(self,
               switch: str,
               argument_value: str,
               validator: str,
               description: str,
               name: Optional[str]=None,
               stacktrace: Optional[str]=None,
               critical: bool=False,
               unexpected: bool=False) -> None:
    """Initializes the DFTimewolfError with provided or default message."""
    self.name = name
    self.stacktrace = stacktrace
    self.critical = critical
    self.unexpected = unexpected
    self.switch = switch
    self.argument_value = argument_value
    self.validator = validator
    self.description = description
    message = (f'Invalid argument: "{switch}" with value "{argument_value}". '
               f'Determined by "{validator}" validator. Error: {description}')
    super(DFTimewolfError, self).__init__(message)



class RecipeArgsValidatorError(DFTimewolfError):
  """Fatal error in recipe argument validation."""
