"""Generic error wrapper"""

class DFTimewolfError(Exception):
  """Class to represent a DFTimewolfError."""

  message = 'An error occurred.'

  def __init__(self, message):
    Exception.__init__(self)
    self.message = message
