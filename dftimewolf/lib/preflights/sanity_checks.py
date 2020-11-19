"""Sanity checks for recipes."""
from __future__ import print_function

import datetime

from dftimewolf.lib import module
from dftimewolf.lib.errors import DFTimewolfError
from dftimewolf.lib.modules import manager as modules_manager

# pylint: disable=line-too-long
DATE_ORDER_ERROR_STRING = 'Hold fast time traveller, your start date {0:s} is after your end date {1:s}'

class SanityChecks(module.PreflightModule):
  """Verifies logic of parameters and fails fast on issues."""

  def __init__(self, state, name=None, critical=False):
    super(SanityChecks, self).__init__(
        state, name=name, critical=critical)
    self.startdate = None
    self.enddate = None
    self.dateformat = None


  def SetUp(self, startdate=None, enddate=None, dateformat=None):  # pylint: disable=arguments-differ
    """Sets up a SanityChecks instance.

    Args:
      startdate (string): A start date of a timespan
      enddate (string): An end date of a timespan
      dateformat (string): A date format suitable for datetime.strptime()
    """
    self.startdate = startdate
    self.enddate = enddate
    self.dateformat = dateformat

  def Process(self):
    """Test whether the values we've received are sane."""

    if (self.startdate and self.enddate and self.dateformat):
      self._AreDatesValid()

  def _AreDatesValid(self):
    """Test the dates we've received, if any, are sane."""

    try:
      start = datetime.datetime.strptime(self.startdate, self.dateformat)
      end = datetime.datetime.strptime(self.enddate, self.dateformat)
      if start > end:
        self.ModuleError(
            DATE_ORDER_ERROR_STRING.format(self.startdate, self.enddate),
            critical=True)
    except (ValueError) as exception:  # Date parsing failure
      self.ModuleError(str(exception), critical=True)

  def CleanUp(self):
    # We don't need to do any cleanup
    return

modules_manager.ModulesManager.RegisterModule(SanityChecks)
