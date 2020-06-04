# -*- coding: utf-8 -*-
"""Local file system exporter module."""

import os
import shutil
import tempfile

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
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
    if not target_directory:
      target_directory = tempfile.mkdtemp()
    elif os.path.exists(target_directory):
      target_directory = os.path.join(target_directory, 'dftimewolf')
    self._target_directory = target_directory

  def Process(self):
    """Checks whether the paths exists and updates the state accordingly."""
    for file_container in self.state.GetContainers(containers.File):
      try:
        self._CopyFileOrDirectory(file_container.path, self._target_directory)
      except OSError as exception:
        self.state.AddError(
            'Could not copy files to {0:s}: {1!s}'.format(
                self._target_directory, exception),
            critical=True)
        return
      print('{0:s} -> {1:s}'.format(file_container.path,
                                    self._target_directory))

  def _CopyFileOrDirectory(self, source, destination_directory):
    """Recursively copies files from source to destination_directory.

    Files will be copied to `destination_directory`'s root. Directories
    will be copied to subdirectories in `destination_directory`.

    Args:
      source (str): source file or directory to copy into the destination
          directory.
      destination_directory (str): destination directory in which to copy
          source.
    """
    counter = 0
    if os.path.isdir(source):
      try:
        shutil.copytree(source, destination_directory)
      except FileExistsError:
        newdir = os.path.join(destination_directory, str(counter))
        shutil.copytree(source, newdir)
        counter += 1
    else:
      shutil.copy2(source, destination_directory)


modules_manager.ModulesManager.RegisterModule(LocalFilesystemCopy)
