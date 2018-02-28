import sys

class DFTimewolfState(object):

  def __init__(self):
    self.errors = []
    self.global_errors = []
    self.current_module = None
    self.input = []
    self.output = []

  def add_error(self, error, critical=False):
    self.errors.append((error, critical))

  def set_current_module(self, module):
    self.current_module = module

  def status(self):
    print "input: ", self.input
    print "output: ", self.output

  def cleanup(self):
    # Move any existing errors to global errors
    self.global_errors.extend(self.errors)
    self.errors = []

    # Make the previous module's output available to the next module
    self.input = self.output
    self.output = []

  def check_errors(self):
    if self.errors:
      print 'dfTimewolf encountered one or more errors:'
      for error, critical in self.errors:
        print '  ' + error
        if critical:
          print 'Critical error found. Aborting.'
          sys.exit(-1)

  def check_global_errors(self):
    if self.global_errors:
      print 'dfTimewolf encountered one or more errors:'
      for error, critical in self.global_errors:
        print '  ' + error
