# -*- coding: utf-8 -*-
"""Reads logs from a GCP cloud project."""
from __future__ import print_function
from __future__ import unicode_literals

import json
import tempfile

from google.api_core import exceptions as google_api_exceptions
from google.auth import exceptions as google_auth_exceptions
from google.cloud import logging
from googleapiclient.errors import HttpError
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import ApplicationDefaultCredentialsError

from dftimewolf.lib import module
from dftimewolf.lib.containers import StackdriverLogs
# Need to register with in the protobuf registry.
# pylint: disable=unused-import
from dftimewolf.lib.collectors import audit_log_pb2 as _


# Monkey patching the ProtobufEntry because of various issues, notably
# https://github.com/googleapis/google-cloud-python/issues/7918
def custom_to_api_repr(self):
  """API repr (JSON format) for entry."""
  info = super(logging.entries.ProtobufEntry, self).to_api_repr()
  info['protoPayload'] = self.payload
  return info


logging.entries.ProtobufEntry.to_api_repr = custom_to_api_repr


class StackdriverLogsCollector(module.BaseModule):
  """Collector for Stackdriver logs."""

  def cleanup(self):
    pass

  def __init__(self, state):
    """Initializes a Stackdriver logs collector."""
    super(StackdriverLogsCollector, self).__init__(state)
    self._project_name = None
    self._filter_expression = None

  # pylint: disable=arguments-differ
  def setup(self, project_name, filter_expression):
    """Sets up a a Stackdriver logs collector.

    Args:
      project_name (str): name of the project to fetch logs from.
      filter_expression (str): Stackdriver advanced logs filter expression.
    """
    self._project_name = project_name
    self._filter_expression = filter_expression

  def process(self):
    """Copies logs from a cloud project."""
    descending = logging.DESCENDING

    output_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, encoding='utf-8')
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
      self.state.add_error(
          'Error accessing project: {0!s}'.format(exception), critical=True)
      return

    except google_api_exceptions.InvalidArgument as exception:
      self.state.add_error(
          'Unable to parse filter {0:s} with error {1:s}'.format(
              self._filter_expression, exception), critical=True)
      return

    except AccessTokenRefreshError as exception:
      self.state.add_error(
          'Something is wrong with your gcloud access token.')
      self.state.add_error(exception, critical=True)
      return

    except (ApplicationDefaultCredentialsError,
            google_auth_exceptions.DefaultCredentialsError) as exception:
      self.state.add_error(
          'Something is wrong with your Application Default Credentials. '
          'Try running:\n $ gcloud auth application-default login')
      self.state.add_error(exception, critical=True)
      return

    except HttpError as exception:
      if exception.resp.status == 403:
        self.state.add_error(
            'Make sure you have the appropriate permissions on the project')
      if exception.resp.status == 404:
        self.state.add_error(
            'GCP resource not found. Maybe a typo in the project name?')
      self.state.add_error(exception, critical=True)
      return

    print('[stackdriver] Downloaded logs to {0:s}'.format(output_path))
    output_file.close()

    logs_report = StackdriverLogs(
        path=output_path, filter_expression=self._filter_expression,
        project_name=self._project_name)
    self.state.store_container(logs_report)
