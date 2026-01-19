# -*- coding: utf-8 -*-
"""Pulls audit logs from Google Workspace."""

import datetime
import os.path
import json
import re
import tempfile

from typing import Optional, Callable

import filelock
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import cache
from dftimewolf.lib import telemetry
from dftimewolf.lib.containers import manager as container_manager


RE_TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
WORKSPACE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

class WorkspaceAuditCollector(module.BaseModule):
  """Collector for Google Workspace Audit logs. """

  SCOPES = ['https://www.googleapis.com/auth/admin.reports.audit.readonly']
  _CREDENTIALS_FILENAME = '.dftimewolf_workspace_credentials.json'
  _CLIENT_SECRET_FILENAME = '.dftimewolf_workspace_client_secret.json'

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initializes a Workspace Audit Log collector."""
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)
    self._credentials: Optional[Credentials] = None
    self._application_name = ''
    self._filter_expression = ''
    self._user_key = 'all'
    self._start_time = None  # type: Optional[datetime.datetime]
    self._end_time = None # type: Optional[datetime.datetime]

  def _BuildAuditResource(self, credentials: Optional[Credentials]
                          ) -> discovery.Resource:
    """Builds a reports resource object to use to request logs.

    Args:
      credentials: Google API credentials

    Returns:
      A resource object for interacting with the Workspace audit API.
    """
    service = discovery.build('admin', 'reports_v1', credentials=credentials)
    return service

  def _GetCredentials(self) -> Optional[Credentials]:
    """Obtains API credentials for accessing the Workspace audit API.

    Returns:
      google.oauth2.credentials.Credentials: Google API credentials.
    """
    credentials: Optional[Credentials] = None

    # The credentials file stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    credentials_path = os.path.join(
        os.path.expanduser('~'), self._CREDENTIALS_FILENAME)
    lock = filelock.FileLock(credentials_path + '.lock')  # pylint: disable=abstract-class-instantiated
    with lock:
      if os.path.exists(credentials_path):
        try:
          credentials = Credentials.from_authorized_user_file(
              credentials_path, self.SCOPES)
        except ValueError as exception:
          self.logger.warning(
              f'Unable to load credentials: {exception:s}')
          credentials = None

      # If there are no (valid) credentials available, let the user log in.
      if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
          credentials.refresh(Request())
        else:
          secrets_path = os.path.join(
              os.path.expanduser('~'), self._CLIENT_SECRET_FILENAME)
          if not os.path.exists(secrets_path):
            error_message = (
                'No OAuth application credentials available to retrieve '
                'workspace logs. Please generate OAuth application credentials '
                '(see https://developers.google.com/workspace/guides/'
                'create-credentials#desktop) and save them to {0:s}.').format(
                    secrets_path)
            self.ModuleError(error_message, True)
          flow = InstalledAppFlow.from_client_secrets_file(
              secrets_path, self.SCOPES)
          credentials = flow.run_local_server()

        # Save the credentials for the next run
        if credentials:
          with open(credentials_path, 'w') as token_file:
            token_file.write(credentials.to_json())

    return credentials

  # pylint: disable=arguments-differ
  def SetUp(self,
            application_name: str,
            filter_expression: str,
            user_key: str='all',
            start_time: Optional[datetime.datetime]=None,
            end_time: Optional[datetime.datetime]=None) -> None:
    """Sets up a Workspace Audit logs collector.

    Args:
      application_name: name of the application to fetch logs for. See
          https://developers.google.com/admin-sdk/reports/reference/rest/v1
          /activities/list#ApplicationName
      filter_expression: Workspace logs filter expression.
      user_key: profile ID or email for which data should be
          collected. Can be 'all' for all users.
      start_time: Beginning of the time period to return results for.
      end_time: End of the time period to return results for.
    """

    # Omit '-' delimiter from the filter_expression (meeting_id) for
    # the meet application
    if application_name == 'meet' and '-' in filter_expression:
      filter_expression = filter_expression.replace('-', '')
      self.logger.debug("Found '-' delimiter in the meeting_id and removed it!")

    self._credentials = self._GetCredentials()
    self._application_name = application_name
    self._filter_expression = filter_expression
    self._user_key = user_key

    self._end_time = end_time
    self._start_time = start_time

    if start_time:
      now = datetime.datetime.now(tz=datetime.timezone.utc)

      if start_time < now - datetime.timedelta(days=180):
        max_date = (now - datetime.timedelta(days=180)).strftime(
          '%Y-%m-%dT%H:%M:%SZ')
        self.ModuleError(
            'Maximum gWorkspace retention is 6 months. '
            'Please choose a more recent start date '
            f'(Earliest: {max_date}).', critical=True)

  def Process(self) -> None:
    """Copies audit logs from a Google Workspace log."""
    output_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, encoding='utf-8', suffix='.jsonl')
    output_path = output_file.name
    self.logger.info(f"Downloading logs to {output_path:s}")

    audit_resource = self._BuildAuditResource(self._credentials)
    request_parameters = {
        'userKey': self._user_key,
        'applicationName': self._application_name
    }
    if self._filter_expression:
      request_parameters['filters'] = self._filter_expression
    if self._start_time:
      request_parameters['startTime'] = self._start_time.strftime(
          WORKSPACE_TIME_FORMAT)
    if self._end_time:
      request_parameters['endTime'] = self._end_time.strftime(
          WORKSPACE_TIME_FORMAT)

    try:
      # Pylint can't see the activities method.
      # pylint: disable=no-member
      request = audit_resource.activities().list(**request_parameters)
      while request is not None:
        response = request.execute()
        audit_records = response.get('items', [])
        for audit_record in audit_records:
          output_file.write(json.dumps(audit_record))
          output_file.write('\n')

        # Pylint can't see the activities method.
        # pylint: disable=no-member
        request = audit_resource.activities().list_next(request, response)
    except (RefreshError, DefaultCredentialsError) as exception:
      self.ModuleError(
          'Something is wrong with your gcloud access token or '
          'Application Default Credentials. Try running:\n '
          '$ gcloud auth application-default login')
      self.ModuleError(str(exception), critical=True)

    logs_report = containers.WorkspaceLogs(
        application_name=self._application_name, path=output_path,
        filter_expression=self._filter_expression, user_key=self._user_key,
        start_time=self._start_time, end_time=self._end_time)
    self.logger.info(f'Downloaded logs to {output_path}')
    self.StoreContainer(logs_report)


modules_manager.ModulesManager.RegisterModule(WorkspaceAuditCollector)
