# -*- coding: utf-8 -*-
"""Class definition for DFTimewolf modules."""


class BaseModule(object):
  """Base class for Modules.

  Attributes:
    critical: Boolean indicating whether the execution of this module is
        critical to the execution of the recipe. If set to True, and the module
        fails to properly run, the recipe will be aborted.
    input: variable containing elements to be processed by a module.
    output: variable containing the output of a module's execution.
  """

  def __init__(self, state, critical=False):
    """Initialize the base collector object.

    Args:
      state: a DFTimewolfState object.
      critical: Whether the module is critical or not. If True and the module
          encounters an error, then the whole recipe will fail.
    """
    super(BaseModule, self).__init__()
    self.critical = critical
    self.state = state

  def setup(self, *args, **kwargs):
    """Sets up necessary module configuration options."""
    raise NotImplementedError

  def cleanup(self):
    """Cleans up module output to prepare it for the next module."""
    raise NotImplementedError

  def process(self):
    """Processes input and builds the module's output attribute.

    Modules take input information and process it into output information,
    which can in turn be ingested as input information by other modules.
    """
    raise NotImplementedError
