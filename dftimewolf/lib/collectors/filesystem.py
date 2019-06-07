# -*- coding: utf-8 -*-
"""Collect artifacts from the local filesystem."""

from __future__ import unicode_literals

import os

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class FilesystemCollector(module.BaseModule):
  """Collect artifacts from the local filesystem.

  input: None, takes input from parameters only.
  output: A list of existing file paths.
  """

  def __init__(self, state):
    super(FilesystemCollector, self).__init__(state)
    self._paths = None

  def setup(self, paths=None):  # pylint: disable=arguments-differ
    """Sets up the _paths attribute.

    Args:
      paths: Comma-separated list of strings representing the paths to collect.
    """
    if not paths:
      self.state.add_error(
          'No `paths` argument provided in recipe, bailing', critical=True)
    else:
      self._paths = [path.strip() for path in paths.strip().split(',')]

  def cleanup(self):
    pass

  def process(self):
    """Checks whether the paths exists and updates the state accordingly."""
    for path in self._paths:
      if os.path.exists(path):
        self.state.output.append((os.path.basename(path), path))
      else:
        self.state.add_error(
            'Path {0:s} does not exist'.format(str(path)), critical=False)
    if not self.state.output:
      self.state.add_error('No valid paths collected, bailing', critical=True)


modules_manager.ModulesManager.RegisterModule(FilesystemCollector)
