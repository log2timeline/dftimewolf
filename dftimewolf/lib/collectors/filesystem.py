# -*- coding: utf-8 -*-
"""Collect artifacts from the local filesystem."""

from __future__ import unicode_literals

import os

from dftimewolf.lib.module import BaseModule


class FilesystemCollector(BaseModule):
  """Collect artifacts from the local filesystem.

  input: None, takes input from parameters only.
  output: A list of existing file paths.
  """

  def __init__(self, state):
    super(FilesystemCollector, self).__init__(state)
    self._paths = None

  def setup(self, paths=None): # pylint: disable=arguments-differ
    """Sets up the _paths attribute

    Args:
      paths: Comma-separated list of strings representing the paths to collect.
    """
    if not paths:
      self.state.add_error(
          'No `paths` argument provided in recipe, bailing', critical=True)
    self._paths = [path.strip() for path in paths.strip().split(',')]

  def cleanup(self):
    pass

  def process(self):
    """Checks whether the paths exists and updates the state accordingly."""
    for path in self._paths:
      if os.path.exists(path):
        self.state.output.append(path)
      else:
        self.state.add_error(
            'Path {0:s} does not exist'.format(str(path)), critical=False)
