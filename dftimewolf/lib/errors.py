"""Generic error wrapper"""

class DFTimewolfError(Exception):
  """Class to represent a DFTimewolfError."""

  fatal = False
  message = 'An error occurred.'

  def __init__(self, message, fatal=False):
    Exception.__init__(self)
    self.message = message
    if fatal:
      self.message = 'CRITICAL: ' + self.message
    self.fatal = fatal
