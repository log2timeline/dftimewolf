# -*- coding: utf-8 -*-
"""Reads logs from a GCP cloud project."""
import json
import tempfile

from google.api_core import exceptions as google_api_exceptions
from google.auth import exceptions as google_auth_exceptions
from google.cloud import logging
from googleapiclient.errors import HttpError

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
# Need to register with in the protobuf registry.
# pylint: disable=unused-import
from dftimewolf.lib.collectors import audit_log_pb2 as _
from dftimewolf.lib.modules import manager as modules_manager


# Monkey patching the ProtobufEntry because of various issues, notably
# https://github.com/googleapis/google-cloud-python/issues/7918
def _CustomToAPIRepr(self):
  """API repr (JSON format) for entry."""
  info = super(logging.entries.ProtobufEntry, self).to_api_repr()
  info['protoPayload'] = self.payload
  return info


logging.entries.ProtobufEntry.to_api_repr = _CustomToAPIRepr


class GCPLogsCollector(module.BaseModule):
  """Collector for Google Cloud Platform logs."""

  def __init__(self, state):
    """Initializes a GCP logs collector."""
    super(GCPLogsCollector, self).__init__(state)
    self._filter_expression = None
    self._project_name = None

  # pylint: disable=arguments-differ
  def SetUp(self, project_name, filter_expression):
    """Sets up a a GCP logs collector.

    Args:
      project_name (str): name of the project to fetch logs from.
      filter_expression (str): GCP advanced logs filter expression.
    """
    self._project_name = project_name
    self._filter_expression = filter_expression

  def Process(self):
    """Copies logs from a cloud project."""
    descending = logging.DESCENDING

    output_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, encoding='utf-8', suffix='.jsonl')
    output_path = output_file.name

    try:
      if self._project_name:
        logging_client = logging.Client(project=self._project_name)
      else:
        logging_client = logging.Client()

      for entry in logging_client.list_entries(
          order_by=descending, filter_=self._filter_expression):

        log_dict = entry.to_api_repr()
        output_file.write(json.dumps(log_dict))
        output_file.write('\n')

    except google_api_exceptions.NotFound as exception:
      self.state.AddError(
          'Error accessing project: {0!s}'.format(exception), critical=True)
      return

    except google_api_exceptions.InvalidArgument as exception:
      self.state.AddError(
          'Unable to parse filter {0:s} with error {1:s}'.format(
              self._filter_expression, exception), critical=True)
      return

    except (google_auth_exceptions.DefaultCredentialsError,
            google_auth_exceptions.RefreshError) as exception:
      self.state.AddError(
          'Something is wrong with your gcloud access token or '
          'Application Default Credentials. Try running:\n '
          '$ gcloud auth application-default login')
      # TODO: determine if exception should be converted into a string as
      # elsewhere in the codebase.
      self.state.AddError(exception, critical=True)
      return

    except HttpError as exception:
      if exception.resp.status == 403:
        self.state.AddError(
            'Make sure you have the appropriate permissions on the project')
      if exception.resp.status == 404:
        self.state.AddError(
            'GCP resource not found. Maybe a typo in the project name?')
      # TODO: determine if exception should be converted into a string as
      # elsewhere in the codebase.
      self.state.AddError(exception, critical=True)
      return

    print('[gcp_logging] Downloaded logs to {0:s}'.format(output_path))
    output_file.close()

    logs_report = containers.GCPLogs(
        path=output_path, filter_expression=self._filter_expression,
        project_name=self._project_name)
    self.state.StoreContainer(logs_report)


modules_manager.ModulesManager.RegisterModule(GCPLogsCollector)
