# -*- coding: utf-8 -*-
"""Collects osquery from the command line and the local file system."""

import json
import os
from typing import Optional, List

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState

_ALL_PLATFORMS = ['darwin', 'freebsd', 'linux', 'windows']

class OsqueryCollector(module.BaseModule):
  """Osquey query collector.

  Attributes:
      osqueries (List[containers.OsqueryQuery]): list of osquery containers.
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
    self.osqueries: List[containers.OsqueryQuery] = []

  def _ValidateOsquery(self, query: str) -> bool:
    """Validate Osquery query.

    Args:
      query (str): osquery query.

    Returns:
      True if the query appears to be valid, False otherwise
    """
    # TODO(sydp): add more checks.
    return query.upper().startswith('SELECT ')

  def _ParsePlatforms(self, platforms: str) -> List[str]:
    """Parse and normalise the platforms value from an osquery pack.

    Arguments:
      platforms: the platforms value from an osquery pack.

    Returns:
      a list of operating system platforms.  Valid values in the list are
      'darwin', 'freebsd', 'linux', 'windows'
    """
    if not platforms:
      return []

    unique_platforms = set()
    for platform in platforms.split(','):
      platform = platform.strip()
      if platform in ('all', 'any'):
        unique_platforms.update(_ALL_PLATFORMS)
      elif platform == 'posix':
        unique_platforms.update(['darwin', 'freebsd', 'linux'])
      elif platform in _ALL_PLATFORMS:
        unique_platforms.add(platform)
      else:
        self.logger.warning(f'Unexpected value {platform} in platform value.')

    return list(unique_platforms)

  def _LoadOsqueryPackToState(self, path: str) -> None:
    """Loads osquery from an osquery pack file and creates Osquery containers.

    Args:
      path: the path to the JSON file.
    """
    with open(path, mode='r') as fd:
      global_platform = []

      query_pack = json.load(fd)

    # A 'global' platform value can be set at the root level
    if 'platform' in query_pack:
      global_platform = self._ParsePlatforms(query_pack.get('platform'))

    for num, (name, entry) in enumerate(
        query_pack.get('queries', {}).items()):
      query = entry['query']
      if not self._ValidateOsquery(query):
        self.logger.warning(f'Entry {num} in query pack'
                            f'{path} does not appear to be valid.')
        continue

      if 'platform' in entry:
        platform = self._ParsePlatforms(entry.get('platform'))
      else:
        platform = global_platform
      self.osqueries.append(
          containers.OsqueryQuery(
              query=query,
              name=name,
              description=entry.get('description', ''),
              platforms=platform))

  def _LoadTextFileToState(self, path: str) -> None:
    """Loads osquery from a text file and creates Osquery containers.

    Args:
      path: the path to the text file.
    """
    with open(path, mode='r') as fd:
      for line_number, line in enumerate(fd.readlines()):
        if self._ValidateOsquery(line):
          self.osqueries.append(
              containers.OsqueryQuery(
                  query=line,
                  name='',
                  description='',
                  platforms=None))
        else:
          self.logger.warning(f'Osquery on line {line_number} of {path} '
                              'does not appear to be valid.')

  # pylint: disable=arguments-differ
  def SetUp(self,
            query: str,
            paths: str) -> None:
    """Sets up the osquery to collect.

    Supported files are:
    * text files that contain one Osquery
    * json files containing an osquery pack. See https://osquery.readthedocs.io
          /en/stable/deployment/configuration/#query-packs for details and
          https://github.com/osquery/osquery/tree/master/packs for examples.

    Args:
      query (str): osquery query.
      paths (str): osquery filepaths.
    """
    if not query and not paths:
      self.ModuleError('Both query and paths cannot be empty.', critical=True)

    if query and self._ValidateOsquery(query):
      self.osqueries.append(containers.OsqueryQuery(query=query))
    else:
      self.logger.warning(
          'Osquery parameter not set or does not appear to be valid.')

    if paths:
      split_paths = [path.strip() for path in paths.split(',')]

      for path in split_paths:
        if not os.path.exists(path):
          self.logger.warning(f'Path {path} does not exist.')
          continue
        if os.path.splitext(path)[1] == '.json':
          self._LoadOsqueryPackToState(path)
        else:
          self._LoadTextFileToState(path)

    if not self.osqueries:
      self.ModuleError(
        message='No valid osquery collected.', critical=True)

  def Process(self) -> None:
    """Collects osquery from the command line and local file system."""
    for osquery in self.osqueries:
      self.state.StoreContainer(osquery)


modules_manager.ModulesManager.RegisterModule(OsqueryCollector)
