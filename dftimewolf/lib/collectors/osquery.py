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
      osqueries (List[str]): list of osquery queries.
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
    self.osqueries: List[str] = []

  def _ValidateOsquery(self, query: str) -> bool:
    """Validate Osquery query.

    Args:
      query (str): osquery query.

    Returns:
      True if the query appears to be valid, False otherwise
    """
    # TODO(sydp): add more checks.
    return query.upper().startswith('SELECT ')

  # pylint: disable=arguments-differ
  def SetUp(self,
            query: str,
            paths: str) -> None:
    """Sets up the paths to collect.

    Args:
      query (str): osquery query.
      paths (str): osquery filepaths.
    """
    if not query and not paths:
      self.ModuleError('Both query and paths cannot be empty.', critical=True)

    if self._ValidateOsquery(query):
      self.osqueries.append(query)
    else:
      self.logger.warning('Osquery parameter does not appear to be valid.')

    if paths:
      split_paths = [path.strip() for path in paths.split(',')]

      for path in split_paths:
        if not os.path.exists(path):
          self.logger.warning('Path {0:s} does not exist.'.format(path))
          continue

        with open(path, mode='r') as fd:
          for line_number, line in enumerate(fd.readlines()):
            if self._ValidateOsquery(line):
              self.osqueries.append(line)
            else:
              self.logger.warning(f'Osquery on line {line_number} of {path} does'
                                  ' not appear to be valid.')

    if not self.osqueries:
      self.ModuleError(
        message='No valid osquery collected.', critical=True)

  def Process(self) -> None:
    """Collects osquery from the command line and local file system."""
    for osquery in self.osqueries:
      container = containers.OsqueryQuery(osquery)
      self.state.StoreContainer(container)


modules_manager.ModulesManager.RegisterModule(OsqueryCollector)
