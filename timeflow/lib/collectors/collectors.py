"""Timeflow artifact collectors, responsible for collecting artifacts."""

__author__ = u'jbn@google.com (Johan Berggren)'

import threading

from timeflow.lib import utils


class BaseCollector(threading.Thread):
  """Base class for collectors.

  Attributes:
    console_out: Console output helper
  """

  def __init__(self, verbose):
    """Initialize the base collector object.

    Args:
      verbose: (Optional[bool]) whether verbose output is desired.
    """
    super(BaseCollector, self).__init__()
    self.console_out = utils.TimeflowConsoleOutput(
        sender=self.__class__.__name__, verbose=verbose)
    self.results = []

  def run(self):
    self.results = self.collect()

  def collect(self):
    """Collect artifacts.

    Returns:
      list(tuple): containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.
    """
    raise NotImplementedError

  @property
  def collection_name(self):
    """Name for the collection of artifacts."""
    raise NotImplementedError
