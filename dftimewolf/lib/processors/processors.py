"""DFTimewolf artifact processors, responsible for processing artifacts."""

__author__ = u'jbn@google.com (Johan Berggren)'

import threading

from dftimewolf.lib import utils


class BaseArtifactProcessor(threading.Thread):
  """Base class for artifact processors."""

  def __init__(self, verbose):
    super(BaseArtifactProcessor, self).__init__()
    self.console_out = utils.DFTimewolfConsoleOutput(
        sender=self.__class__.__name__, verbose=verbose)

  def run(self):
    """Threads the process() method."""
    self.process()

  def process(self):
    """Process artifacts.

    Returns:
      str: path to a file containing results of processing.
    """
    raise NotImplementedError
