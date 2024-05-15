# -*- coding: utf-8 -*-
"""Reads logs from an Azure subscription."""
import json
import tempfile
from typing import Optional

from azure.mgmt import monitor as az_monitor
from azure.core import exceptions as az_exceptions

from libcloudforensics import errors as lcf_errors
from libcloudforensics.providers.azure.internal import common as lcf_common

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class AzureLogsCollector(module.BaseModule):
  """Collector for Azure Activity logs."""

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes an Azure logs collector."""
    super(AzureLogsCollector, self).__init__(
        state, name=name, critical=critical)
    self._filter_expression = ''
    self._subscription_id = ''
    self._profile_name: Optional[str] = ''

  # pylint: disable=arguments-differ
  def SetUp(self,
            subscription_id: str,
            filter_expression: str,
            profile_name: Optional[str]=None) -> None:
    """Sets up an Azure logs collector.

    Args:
      subscription_id (str): name of the subscription_id to fetch logs from.
      filter_expression (str): Azure logs filter expression.
      profile_name (str): a profile name to use for finding credentials.
    """
    self._subscription_id = subscription_id
    self._filter_expression = filter_expression
    self._profile_name = profile_name

  def Process(self) -> None:
    """Copies logs from an Azure subscription."""

    output_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, encoding='utf-8', suffix='.jsonl')
    output_path = output_file.name
    self.PublishMessage(f"Downloading logs to {output_path:s}")

    try:
      _, credentials = lcf_common.GetCredentials(
          profile_name=self._profile_name)
    except (lcf_errors.CredentialsConfigurationError,
            FileNotFoundError) as exception:
      self.ModuleError('Ensure credentials are properly configured as expected '
          'by libcloudforensics: either a credentials.json file associated '
          'with the provided profile_name, environment variables as per '
          'https://docs.microsoft.com/en-us/azure/developer/python/azure-sdk-authenticate ' # pylint: disable=line-too-long
          ', or Azure CLI credentials.')
      self.ModuleError(str(exception), critical=True)

    monitoring_client = az_monitor.MonitorManagementClient(
        credentials, self._subscription_id)
    activity_logs_client = monitoring_client.activity_logs

    try:
      results = activity_logs_client.list(filter=self._filter_expression)

      while True:
        try:
          result_entry = next(results)
        except StopIteration:
          break

        log_dict = result_entry.as_dict()
        output_file.write(json.dumps(log_dict))
        output_file.write('\n')

    except az_exceptions.ClientAuthenticationError as exception:
      self.ModuleError('Ensure credentials are properly configured.')
      self.ModuleError(str(exception), critical=True)

    except az_exceptions.HttpResponseError as exception:
      if exception.status_code == 400:
        self.ModuleError(
            'Badly formed request, ensure that the filter expression is '
            'formatted correctly e.g. "eventTimestamp ge \'2022-02-01\'"')
      if exception.status_code == 403:
        self.ModuleError(
            'Make sure you have the appropriate permissions in the '
            'subscription')
      if exception.status_code == 404:
        self.ModuleError(
            'Resource not found, ensure that subscription_id is correct.')
      self.ModuleError(str(exception), critical=True)

    self.PublishMessage('Downloaded logs to {output_path}')
    output_file.close()

    logs_report = containers.File('AzureLogsCollector result', output_path)
    self.StoreContainer(logs_report)


modules_manager.ModulesManager.RegisterModule(AzureLogsCollector)
