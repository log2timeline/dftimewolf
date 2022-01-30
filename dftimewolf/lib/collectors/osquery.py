# -*- coding: utf-8 -*-
"""Collects osquery from the command line and the local file system."""

import os
from typing import Optional, List

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class OsqueryCollector(module.BaseModule):
  """Osquey query collector.

  Attributes:
      query (str): osquery query.
      paths (List[str]): list of file paths where each file contains osquery
          queries (one per line).
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
    super(OsqueryCollector, self).__init__(
        state, name=name, critical=critical)
    self.query: str = ""
    self.paths: List[str] = []

  # pylint: disable=arguments-differ
  def SetUp(self,
            query: str,
            paths: str) -> None:
    """Sets up the paths to collect.

    Args:
      query (str): osquery query.
      files (str): osquery filepaths
    """
    if not query and not paths:
      self.ModuleError('Both query and files cannot be empty.', critical=True)

    if query:
      self.query = query

    if paths:
      self.paths = [path.strip() for path in paths.split(',')]

  def Process(self) -> None:
    """Collects osquery from the command line and local file system."""
    osquery_queries = []
    if not self.query.upper().startswith('SELECT '):
      self.logger.warning(
          'Osquery parameter does not start with SELECT.')
    else:
      osquery_queries.append(self.query)

    for path in self.paths:
      if not os.path.exists(path):
        self.logger.warning('Path {0:s} does not exist'.format(path))
        continue

      with open(path, mode='r') as fd:
        for line_number, line in enumerate(fd.readlines()):
          if not line.upper().startswith('SELECT '):
            self.logger.warning('Osquery on line {0:d} of {1:s} does not start '
                                'with SELECT.'.format(line_number, path))
          else:
            osquery_queries.append(self.query)

    if not osquery_queries:
      self.ModuleError(
        message='No valid osquery collected.', critical=True)

    for osquery in osquery_queries:
      container = containers.OsqueryQuery(osquery)
      self.state.StoreContainer(container)


modules_manager.ModulesManager.RegisterModule(OsqueryCollector)
