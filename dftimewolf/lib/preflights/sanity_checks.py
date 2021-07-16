"""Sanity checks for recipes."""
from __future__ import print_function

import datetime
from typing import Optional

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState

# pylint: disable=line-too-long
DATE_ORDER_ERROR_STRING = 'Hold fast time traveller, your start date {0:s} is after your end date {1:s}'

class SanityChecks(module.PreflightModule):
  """Verifies logic of parameters and fails fast on issues."""

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    super(SanityChecks, self).__init__(
        state, name=name, critical=critical)
    self.startdate = str()
    self.enddate = str()
    self.dateformat = str()


  def SetUp(self,  # pylint: disable=arguments-differ
            startdate: str,
            enddate: str,
            dateformat: str) -> None:
    """Sets up a SanityChecks instance.

    Args:
      startdate (string): A start date of a timespan
      enddate (string): An end date of a timespan
      dateformat (string): A date format suitable for datetime.strptime()
    """
    self.startdate = startdate
    self.enddate = enddate
    self.dateformat = dateformat

  def Process(self) -> None:
    """Test whether the values we've received are sane."""

    if (self.startdate and self.enddate and self.dateformat):
      self._AreDatesValid()

  def _AreDatesValid(self) -> None:
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
