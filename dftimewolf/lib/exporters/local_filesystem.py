# -*- coding: utf-8 -*-
"""Local file system exporter module."""

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

  def __init__(self, state, name=None, critical=False):
    """Initializes a local file system exporter module."""
    super(LocalFilesystemCopy, self).__init__(
        state, name=name, critical=critical)
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
    if not self._target_directory:
      self._target_directory = tempfile.mkdtemp()
    self._compress = compress
    if not target_directory:
      target_directory = tempfile.mkdtemp(prefix='dftimewolf_local_fs')
    elif os.path.exists(target_directory):
      target_directory = os.path.join(target_directory, 'dftimewolf')
      os.makedirs(target_directory, exist_ok=True)

  def Process(self):
    """Checks whether the paths exists and updates the state accordingly."""
    for file_container in self.state.GetContainers(containers.File, pop=True):
      self.logger.info('{0:s} -> {1:s}'.format(
          file_container.path, self._target_directory))

      if not self._compress:
        try:
          full_paths = self._CopyFileOrDirectory(
              file_container.path, self._target_directory)
        except OSError as exception:
          self.ModuleError(
              'Could not copy files to {0:s}: {1!s}'.format(
                  self._target_directory, exception),
              critical=True)
        for path_ in full_paths:
          file_name = os.path.basename(path_)
          self.state.StoreContainer(containers.File(name=file_name, path=path_))
      else:
        try:
          tar_file = utils.Compress(file_container.path, self._target_directory)
          self.state.StoreContainer(containers.File(
              name=os.path.basename(tar_file), path=tar_file))
          self.logger.info('{0:s} was compressed into {1:s}'.format(
              file_container.path, tar_file))
        except RuntimeError as exception:
          self.ModuleError(exception, critical=True)
          return

  def _CopyFileOrDirectory(self, source, destination_directory):
    """Recursively copies files from source to destination_directory.

    Files will be copied to `destination_directory`'s root. Directories
    will be copied to subdirectories in `destination_directory`.

    Args:
      source (str): source file or directory to copy into the destination
          directory.
      destination_directory (str): destination directory in which to copy
          source.

    Returns:
      list[str]: The full copied output paths.
    """
    counter = 0
    full_paths = []
    if os.path.isdir(source):
      try:
        shutil.copytree(source, destination_directory)
        full_paths.append(destination_directory)
      except FileExistsError:
        new_directory = os.path.join(destination_directory, str(counter))
        shutil.copytree(source, new_directory)
        full_paths.append(new_directory)
        counter += 1
    else:
      shutil.copy2(source, destination_directory)
      full_paths.append(os.path.join(destination_directory, source))

    return full_paths


modules_manager.ModulesManager.RegisterModule(LocalFilesystemCopy)
