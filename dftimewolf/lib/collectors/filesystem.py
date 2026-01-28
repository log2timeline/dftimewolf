# -*- coding: utf-8 -*-
"""Collects artifacts from the local file system."""

import os
from typing import Callable, List

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import cache
from dftimewolf.lib import telemetry
from dftimewolf.lib.containers import manager as container_manager


class FilesystemCollector(module.BaseModule):
  """Local file system collector.

  input: None, takes input from parameters only.
  output: A list of existing file paths.
  """

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initializes a local file system collector.

    Args:
      name: The modules runtime name.
      container_manager_: A common container manager object.
      cache_: A common DFTWCache object.
      telemetry_: A common telemetry collector object.
      publish_message_callback: A callback to send modules messages to.
    """
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)
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
      self.StoreContainer(container)


modules_manager.ModulesManager.RegisterModule(FilesystemCollector)
