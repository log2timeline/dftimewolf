"""Generic error wrapper"""

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

  def __init__(self, message=None, name=None, stacktrace=None, critical=False,
               unexpected=False):
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
