# -*- coding: utf-8 -*-
"""Class definition for DFTimewolf modules."""

import threading

from dftimewolf.lib import utils


class BaseModule(threading.Thread):
  """Base class for Modules.

  Attributes:
    critical: Boolean indicating whether the execution of this module is
        critical to the execution of the recipe. If set to True, and the module
        fails to properly run, the recipe will be aborted.
    input: list of elements to process
    output: JSON dict of eventual module outputs.
  """

  def __init__(self, critical=False):
    """Initialize the base collector object.

    Args:
      critical: Whether the module is critical or not.
    """
    super(BaseCollector, self).__init__()
    self.critical = critical
    self.output = {}

  def process_input(self, input):
    """Processes input and builds the module's output attribute.

    Modules take input information and process it into output information,
    which can in turn be ingested as input information by other modules.

    Args:
      input: dict: The input information to be processed
    """
    raise NotImplementedError
