class DFTimewolfError(Exception):
  fatal = False
  message = 'An error occurred.'
  def __init__(self, message, fatal=False):
    Exception.__init__(self)
    self.message = messages
    if fatal:
      self.message = 'FATAL: ' + self.message
    self.fatal = fatal
