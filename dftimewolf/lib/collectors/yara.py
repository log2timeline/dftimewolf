# -*- coding: utf-8 -*-
"""Definition of modules for collecting Yara rules from TIPs."""

from typing import Optional

import requests


from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class YetiYaraCollector(module.BaseModule):
  """Collector of Yara rules from Yeti TBB instances.

  Yeti TBB is Apache 2.0 licensed. Stores them in container.YaraRule containers.

  Attributes:
    rule_name_filter: A string by which to filter Yara rule names
    api_key: The Yeti API key to use.
    api_root: The Yeti HTTP API root, e.g. http://localhost:8080/api/
  """
  def __init__(self,
              state: DFTimewolfState,
              name: Optional[str]=None,
              critical: bool=False) -> None:
    """Initializes a YaraCollector module."""
    super(YetiYaraCollector, self).__init__(state, name=name, critical=critical)
    self.rule_name_filter = '' # type: str
    self.api_key = ''  # type: str
    self.api_root = '' # type: str

  # pylint: disable=arguments-differ
  def SetUp(self, rule_name_filter: str, api_key: str, api_root: str) -> None:
    """Sets up the YaraCollector module.

    Args:
      rule_name_filter: A string by which to filter Yara rule names
      api_key: The Yeti API key to use.
      api_root: The Yeti HTTP API root, e.g. http://localhost:8080/api/
    """
    self.logger.info(f'Name filter: {rule_name_filter}')
    self.rule_name_filter = rule_name_filter or ''
    self.api_key = api_key
    self.api_root = api_root

  def Process(self) -> None:

    self.logger.debug(f'Connecting to {self.api_root}...')
    self.api_root = self.api_root.strip('/')
    response = requests.post(
        f'{self.api_root}/indicators/filter/',
        json={'name': self.rule_name_filter, 'type': 'x-yara'},
        headers={'X-Yeti-API': self.api_key},
    )

    response_json = response.json()
    if response.status_code != 200:
      self.logger.error(
        f'Error (HTTP {response.status_code}) retrieving indicators'
        f' from Yeti: {response_json}'
      )
      return

    intel = {}
    for rule in response_json:
      intel[rule["id"]] = rule
    self.logger.info(f'Collected {len(intel)} Yara rules from Yeti')

    for rule in intel.values():
      container = containers.YaraRule(
          name=rule['name'], rule_text=rule['pattern'])
      self.state.StoreContainer(container)

  def PreProcess(self) -> None:
    """"Unused."""

  def PostProcess(self) -> None:
    """"Unused."""

modules_manager.ModulesManager.RegisterModules([
    YetiYaraCollector,
])
