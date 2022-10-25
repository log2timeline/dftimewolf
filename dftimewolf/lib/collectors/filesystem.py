# -*- coding: utf-8 -*-
"""Collects artifacts from the local file system."""

import os
from typing import Optional, List

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class FilesystemCollector(module.BaseModule):
  """Local file system collector.

  input: None, takes input from parameters only.
  output: A list of existing file paths.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a local file system collector.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(FilesystemCollector, self).__init__(
        state, name=name, critical=critical)
    self._paths = [] # type: List[str]

  def SetUp(self, paths: str) -> None:  # pylint: disable=arguments-differ
    """Sets up the paths to collect.

    Args:
      paths (str): Comma-separated paths to collect.
    """
    self._paths = [path.strip() for path in paths.split(',')]

  def Process(self) -> None:
    """Collects paths from the local file system."""
    file_containers = []
    for path in self._paths:
      if os.path.exists(path):
        container = containers.File(os.path.basename(path), path)
        file_containers.append(container)
      else:
        self.logger.warning(f'Path {path:s} does not exist')
    if not file_containers:
      self.ModuleError(
          message='No valid paths collected, bailing',
          critical=True)
    for container in file_containers:
      self.state.StoreContainer(container)


modules_manager.ModulesManager.RegisterModule(FilesystemCollector)
