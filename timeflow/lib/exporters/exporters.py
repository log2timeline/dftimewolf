"""Timeflow exporters, responsible for exporting processing results."""

__author__ = u'jbn@google.com (Johan Berggren)'

import threading

from timeflow.lib import utils


class BaseExporter(threading.Thread):
  """Base class for artifact exporters."""

  def __init__(self, verbose):
    super(BaseExporter, self).__init__()
    self.console_out = utils.TimeflowConsoleOutput(
        sender=self.__class__.__name__, verbose=verbose)

  def run(self):
    """Threads the export() method."""
    self.export()

  def export(self):
    """Export artifacts.

    Returns:
      String containing a reference to the export
    """
    raise NotImplementedError
