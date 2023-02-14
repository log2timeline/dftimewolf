# -*- coding: utf-8 -*-
"""Local file system exporter module."""

import os
import shutil
import tempfile
from typing import List, Optional

from dftimewolf.lib import module, utils
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class LocalFilesystemCopy(module.BaseModule):
  """Copies the files in the previous module's output to a given path.

  input: List of paths to copy the files from.
  output: The directory in which the files have been copied.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a local file system exporter module."""
    super(LocalFilesystemCopy, self).__init__(
        state, name=name, critical=critical)
    self._target_directory = str()
    self._compress = False

  # pylint: disable=arguments-differ
  def SetUp(self,
            target_directory: Optional[str]=None,
            compress: bool=False) -> None:
    """Sets up the _target_directory attribute.

    Args:
      target_directory (Optional[str]): path of the directory in which
          collected files will be copied.
      compress (bool): Whether to compress the resulting directory or not
    """
    self._compress = compress
    if not target_directory:
      self._target_directory = tempfile.mkdtemp(prefix='dftimewolf_local_fs')
    else:
      self._target_directory = target_directory

  def Process(self) -> None:
    """Checks whether the paths exists and updates the state accordingly."""
    self.state.DedupeContainers(containers.File)
    for file_container in self.GetContainers(containers.File, pop=True):
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
          self.StoreContainer(containers.File(name=file_name, path=path_))
      else:
        try:
          tar_file = utils.Compress(file_container.path, self._target_directory)
          self.StoreContainer(containers.File(
              name=os.path.basename(tar_file), path=tar_file))
          self.PublishMessage(
              f'{file_container.path} was compressed into {tar_file}')
        except RuntimeError as exception:
          self.ModuleError(str(exception), critical=True)
          return

  def _CopyFileOrDirectory(
      self, source: str, destination_directory: str) -> List[str]:
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
    full_paths = []
    if os.path.isdir(source):
      try:
        basename = source.split('/')[-1]
        full_paths.append(shutil.copytree(
            source, 
            '/'.join([destination_directory, basename]),
            dirs_exist_ok=True))
      except shutil.Error as e:
        self.ModuleError(str(e), critical=True)
    else:
      try:
        full_paths.append(shutil.copy2(source, destination_directory))
      except shutil.SameFileError as exception:
        self.logger.warning(str(exception))

    return full_paths


modules_manager.ModulesManager.RegisterModule(LocalFilesystemCopy)
