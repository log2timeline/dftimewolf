"""Generic error wrapper"""

class DFTimewolfError(Exception):
  """Class to represent a DFTimewolfError."""

  def __init__(self, message=None):
    super().__init__(message)
    self.message = message or 'An error occurred.'
