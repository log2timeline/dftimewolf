# -*- coding: utf-8 -*-
"""Local file system exporter module."""

from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil
import tempfile

from dftimewolf.lib.containers import containers
from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import utils


class LocalFilesystemCopy(module.BaseModule):
  """Copies the files in the previous module's output to a given path.

  input: List of paths to copy the files from.
  output: The directory in which the files have been copied.
  """

  def __init__(self, state):
    """Initializes a local file system exporter module."""
    super(LocalFilesystemCopy, self).__init__(state)
    self._target_directory = None
    self._compress = None

  # pylint: disable=arguments-differ
  def SetUp(self, target_directory=None, compress=False):
    """Sets up the _target_directory attribute.

    Args:
      target_directory (Optional[str]): path of the directory in which
          collected files will be copied.
      compress (bool): Whether to compress the resulting directory or not
    """
    self._target_directory = target_directory
    self._compress = compress
    if not target_directory:
      self._target_directory = tempfile.mkdtemp()
    elif not os.path.exists(target_directory):
      os.makedirs(target_directory)

  def Process(self):
    """Checks whether the paths exists and updates the state accordingly."""
    for _, path in self.state.input:
      if not self._compress:
        full_paths = self._CopyFileOrDirectory(path, self._target_directory)
        print('{0:s} -> {1:s}'.format(path, self._target_directory))
        for path_ in full_paths:
          self.state.StoreContainer(containers.FSPath(path=path_))
      else:
        try:
          tar_file = utils.Compress(path, self._target_directory)
          self.state.StoreContainer(containers.FSPath(path=tar_file))
          print('{0:s} was compressed into {1:s}'.format(
              path, tar_file))
        except RuntimeError as exception:
          self.state.AddError(exception, critical=True)
          return

  def _CopyFileOrDirectory(self, source, destination_directory):
    """Recursively copies files from source to destination_directory.

    Args:
      source (str): source file or directory to copy into the destination
          directory.
      destination_directory (str): destination directory in which to copy
          source.

    Returns:
      list[str]: The full copied output paths.
    """
    full_paths = []
    if os.path.isdir(source):
      for item in os.listdir(source):
        full_source = os.path.join(source, item)
        full_destination = os.path.join(destination_directory, item)
        shutil.copytree(full_source, full_destination)
        full_paths.append(full_destination)
    else:
      shutil.copy2(source, destination_directory)
      full_paths.append(os.path.join(destination_directory, source))

    return full_paths


modules_manager.ModulesManager.RegisterModule(LocalFilesystemCopy)
