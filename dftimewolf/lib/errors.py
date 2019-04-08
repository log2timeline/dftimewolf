"""Generic error wrapper"""

class DFTimewolfError(Exception):
  """Class to represent a DFTimewolfError."""

  def __init__(self, message=None):
    super(DFTimewolfError, self).__init__(message)
    self.message = message or 'An error occurred.'
