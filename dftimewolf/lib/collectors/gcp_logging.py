# -*- coding: utf-8 -*-
"""Reads logs from a GCP cloud project."""
import json
import tempfile
import time
from typing import Optional, Dict, Any

from google.api_core import exceptions as google_api_exceptions
from google.auth import exceptions as google_auth_exceptions
from google.cloud import logging
from google.cloud.logging_v2 import entries
from googleapiclient.errors import HttpError

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState

# Monkey patching the ProtobufEntry because of various issues, notably
# https://github.com/googleapis/google-cloud-python/issues/7918

def _CustomToAPIRepr(self: entries.ProtobufEntry) -> Dict[str, Any]:
  """API repr (JSON format) for entry."""
  info = super(entries.ProtobufEntry, self).to_api_repr()  # type: ignore
  info['protoPayload'] = self.payload  # type: ignore
  return info  # type: ignore


entries.ProtobufEntry.to_api_repr = _CustomToAPIRepr  # type: ignore


class GCPLogsCollector(module.BaseModule):
  """Collector for Google Cloud Platform logs."""

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a GCP logs collector."""
    super(GCPLogsCollector, self).__init__(state, name=name, critical=critical)
    self._filter_expression = ''
    self._project_name = ''
    self._backoff = False
    self._delay = 0

  def OutputFile(self):
    """Generate an output file name and path"""
    output_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, encoding='utf-8', suffix='.jsonl')
    output_path = output_file.name
    self.logger.info(f'Downloading logs to {output_path}')
    return output_file, output_path

  def SetupLoggingClient(self):
    """Sets up a GCP Logging Client
    
    Args:
      N/A
    """
    if self._project_name:
      return logging.Client(_use_grpc=False,  # type: ignore
                                        project=self._project_name)
    else:
      return logging.Client(_use_grpc=False)  # type: ignore
  
  def ListPages(self, logging_client):
    """Returns pages based on a Cloud Logging filter
    
    Args:
      logging_client: A GCP Cloud Logging client
    """
    results = logging_client.list_entries(  # type: ignore
          order_by=logging.DESCENDING,
          filter_=self._filter_expression,
          page_size=1000)
    return results.pages

  def ProcessPages(self, pages, backoff_multiplier, output_file, output_path):
    """Iterates through a generator or pages and saves logs to disk.
    Can optionally perform exponential backoff if query API limits are exceeded.
    
    Args:
      pages (generator): A google cloud logging list_entries generator pages object
      backoff_multiplier (str): Query delay multiplier if the API quota is met and backoff is enabled
      output_file (str): Output file name
      output_path (str): Output file path
    
    Returns:
      output_path (str): Log output path (may have been updated if API quota was exceeded)
    """
    while True:
      try:
        time.sleep(self._delay)
        page = next(pages)
      except google_api_exceptions.TooManyRequests as exception:
        self.PublishMessage('Hit quota limit requesting GCP logs.')
        if self._backoff is True:
          self.PublishMessage('Retrying in 60 seconds with a slower query rate.')
          self.PublishMessage('Due to the GCP logging API, the query must restart from the beginning')
          time.sleep(60)
          if self._delay == 0:
            self._delay = 1
          else:
            self._delay *= backoff_multiplier
          self.logger.debug('Setting up new logging client.')
          logging_client = self.SetupLoggingClient()
          pages = self.ListPages(logging_client)
          self.PublishMessage(f'Restarting query with an API request rate of 1 per {self._delay}s')
          output_file, output_path = self.OutputFile()
        else:
          self.PublishMessage('Exponential backoff was not enabled, so query has exited.')
          self.PublishMessage('The collection is most likely incomplete.', is_error=True)
      except StopIteration:
        break

      for entry in page:
        log_dictionary = entry.to_api_repr()
        output_file.write(json.dumps(log_dictionary))
        output_file.write('\n')
    
    return output_path

  # pylint: disable=arguments-differ
  def SetUp(self, project_name: str, filter_expression: str, backoff: bool, delay: str) -> None:
    """Sets up a a GCP logs collector.

    Args:
      project_name (str): name of the project to fetch logs from.
      filter_expression (str): GCP advanced logs filter expression.
      backoff (bool): Retry queries with an increased delay when API quotas are exceeded.
      delay (str): Seconds to wait between retreiving results pages to avoid exceeding API quotas
    """
    self._project_name = project_name
    self._filter_expression = filter_expression
    self._backoff = backoff
    self._delay = float(delay)

  def Process(self) -> None:
    """Copies logs from a cloud project."""

    output_file, output_path = self.OutputFile()

    try:
      'Setup a logging client'
      logging_client = self.SetupLoggingClient()
      
      'Get a generator of query results'
      pages = self.ListPages(logging_client)

      'Iterate through query result pages and save json logs to disk'
      output_path = self.ProcessPages(pages, 2, output_file, output_path)

    except google_api_exceptions.NotFound as exception:
      self.ModuleError(
          f'Error accessing project: {exception!s}', critical=True)

    except google_api_exceptions.InvalidArgument as exception:
      self.ModuleError(
          f'Unable to parse filter {self._filter_expression:s} with error {exception:s}', critical=True)

    except (google_auth_exceptions.DefaultCredentialsError,
            google_auth_exceptions.RefreshError) as exception:
      self.ModuleError(
          'Something is wrong with your gcloud access token or '
          'Application Default Credentials. Try running:\n '
          '$ gcloud auth application-default login')
      # TODO: determine if exception should be converted into a string as
      # elsewhere in the codebase.
      self.ModuleError(exception, critical=True)

    except HttpError as exception:
      if exception.resp.status == 403:
        self.ModuleError(
            'Make sure you have the appropriate permissions on the project')
      if exception.resp.status == 404:
        self.ModuleError(
            'GCP resource not found. Maybe a typo in the project name?')
      self.ModuleError(str(exception), critical=True)

    self.PublishMessage(f'Downloaded logs to {output_path}')
    output_file.close()

    logs_report = containers.GCPLogs(
        path=output_path, filter_expression=self._filter_expression,
        project_name=self._project_name)
    self.state.StoreContainer(logs_report)


modules_manager.ModulesManager.RegisterModule(GCPLogsCollector)
