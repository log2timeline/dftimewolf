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

  # pylint: disable=arguments-differ
  def SetUp(self, project_name: str, filter_expression: str) -> None:
    """Sets up a a GCP logs collector.

    Args:
      project_name (str): name of the project to fetch logs from.
      filter_expression (str): GCP advanced logs filter expression.
    """
    self._project_name = project_name
    self._filter_expression = filter_expression

  def Process(self) -> None:
    """Copies logs from a cloud project."""

    output_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, encoding='utf-8', suffix='.jsonl')
    output_path = output_file.name
    self.logger.info('Downloading logs to {0:s}'.format(output_path))

    try:
      if self._project_name:
        logging_client = logging.Client(_use_grpc=False,  # type: ignore
                                        project=self._project_name)
      else:
        logging_client = logging.Client(_use_grpc=False)  # type: ignore

      results = logging_client.list_entries(  # type: ignore
          order_by=logging.DESCENDING,
          filter_=self._filter_expression,
          page_size=1000)

      pages = results.pages

      while True:
        try:
          page = next(pages)
        except google_api_exceptions.TooManyRequests as exception:
          self.logger.warning(
              'Hit quota limit requesting GCP logs: {0:s}'.format(
                  str(exception)))
          time.sleep(4)
          continue
        except StopIteration:
          break

        for entry in page:

          log_dict = entry.to_api_repr()
          output_file.write(json.dumps(log_dict))
          output_file.write('\n')

    except google_api_exceptions.NotFound as exception:
      self.ModuleError(
          'Error accessing project: {0!s}'.format(exception), critical=True)

    except google_api_exceptions.InvalidArgument as exception:
      self.ModuleError(
          'Unable to parse filter {0:s} with error {1:s}'.format(
              self._filter_expression, exception), critical=True)

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
