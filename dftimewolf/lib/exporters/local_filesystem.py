# -*- coding: utf-8 -*-
"""Collect artifacts from the local filesystem."""

from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil
import tempfile

from dftimewolf.lib import module


class LocalFilesystemCopy(module.BaseModule):
  """Copies the files in the previous module's output to a given path.

  input: List of paths to copy the files from.
  output: The directory in which the files have been copied.
  """

  def __init__(self, state):
    super(LocalFilesystemCopy, self).__init__(state)
    self._target_directory = None

  def setup(self, target_directory=None):  # pylint: disable=arguments-differ
    """Sets up the _target_directory attribute.

    Args:
      target_directory: Directory in which collected files will be dumped.
    """
    self._target_directory = target_directory
    if not target_directory:
      self._target_directory = tempfile.mkdtemp()
    elif not os.path.exists(target_directory):
      try:
        os.makedirs(target_directory)
      except OSError as exception:
        message = 'An unknown error occurred: {0!s}'.format(exception)
        self.state.add_error(message, critical=True)

  def process(self):
    """Checks whether the paths exists and updates the state accordingly."""
    for _, path in self.state.input:
      self._copy_file_or_directory(path, self._target_directory)
      print('{0:s} -> {1:s}'.format(path, self._target_directory))

  def _copy_file_or_directory(self, source, destination_directory):
    """Recursively copies files from source to destination_directory.

    Args:
        source: source file or directory to copy into destination_directory
        destination_directory: destination directory in which to copy source
    """
    if os.path.isdir(source):
      for item in os.listdir(source):
        full_source = os.path.join(source, item)
        full_destination = os.path.join(destination_directory, item)
        shutil.copytree(full_source, full_destination)
    else:
      shutil.copy2(source, destination_directory)
