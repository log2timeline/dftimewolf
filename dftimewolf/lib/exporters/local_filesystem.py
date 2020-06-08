# -*- coding: utf-8 -*-
"""Local file system exporter module."""

import os
import shutil
import tempfile

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class LocalFilesystemCopy(module.BaseModule):
  """Copies the files in the previous module's output to a given path.

  input: List of paths to copy the files from.
  output: The directory in which the files have been copied.
  """

  def __init__(self, state):
    """Initializes a local file system exporter module."""
    super(LocalFilesystemCopy, self).__init__(state)
    self._target_directory = None

  def SetUp(self, target_directory=None):  # pylint: disable=arguments-differ
    """Sets up the _target_directory attribute.

    Args:
      target_directory (Optional[str]): path of the directory in which
          collected files will be copied.
    """
    self._target_directory = target_directory
    if not target_directory:
      self._target_directory = tempfile.mkdtemp()
    elif not os.path.exists(target_directory):
      os.makedirs(target_directory)

  def Process(self):
    """Checks whether the paths exists and updates the state accordingly."""
    for _, path in self.state.input:
      self._CopyFileOrDirectory(path, self._target_directory)
      print('{0:s} -> {1:s}'.format(path, self._target_directory))

  def _CopyFileOrDirectory(self, source, destination_directory):
    """Recursively copies files from source to destination_directory.

    Args:
      source (str): source file or directory to copy into the destination
          directory.
      destination_directory (str): destination directory in which to copy
          source.
    """
    if os.path.isdir(source):
      for item in os.listdir(source):
        full_source = os.path.join(source, item)
        full_destination = os.path.join(destination_directory, item)
        shutil.copytree(full_source, full_destination)
    else:
      shutil.copy2(source, destination_directory)


modules_manager.ModulesManager.RegisterModule(LocalFilesystemCopy)
