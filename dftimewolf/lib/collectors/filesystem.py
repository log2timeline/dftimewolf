# -*- coding: utf-8 -*-
"""Collects artifacts from the local file system."""

import os

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class FilesystemCollector(module.BaseModule):
  """Local file system collector.

  input: None, takes input from parameters only.
  output: A list of existing file paths.
  """

  def __init__(self, state, critical=False):
    """Initializes a local file system collector.

    Args:
      state (DFTimewolfState): recipe state.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(FilesystemCollector, self).__init__(state, critical=critical)
    self._paths = None

  def SetUp(self, paths=None):  # pylint: disable=arguments-differ
    """Sets up the paths to collect.

    Args:
      paths (Optional[str]): Comma-separated paths to collect.
    """
    if not paths:
      self.state.AddError(
          'No `paths` argument provided in recipe, bailing', critical=True)
    else:
      self._paths = [path.strip() for path in paths.split(',')]

  def Process(self):
    """Collects paths from the local file system."""
    for path in self._paths:
      if os.path.exists(path):
        self.state.output.append((os.path.basename(path), path))
      else:
        self.state.AddError(
            'Path {0:s} does not exist'.format(str(path)), critical=False)
    if not self.state.output:
      self.state.AddError('No valid paths collected, bailing', critical=True)


modules_manager.ModulesManager.RegisterModule(FilesystemCollector)
