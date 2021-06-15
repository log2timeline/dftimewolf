# -*- coding: utf-8 -*-
"""Pulls audit logs from Google Workspace."""

import os.path
import filelock
import json
import tempfile

from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager


class WorkspaceAuditCollector(module.BaseModule):
  """Collector for Google Workspace Audit logs. """

  SCOPES = ['https://www.googleapis.com/auth/admin.reports.audit.readonly']
  _CREDENTIALS_FILENAME = '.dftimewolf_workspace_credentials.json'
  _CLIENT_SECRET_FILENAME = '.dftimewolf_workspace_client_secret.json'

  def __init__(self, state, name=None, critical=False):
    """Initializes a Workspace Audit Log collector."""
    super(WorkspaceAuditCollector, self).__init__(state, name=name,
        critical=critical)
    self._start_time = None
    self._credentials = None
    self._application_name = None
    self._filter_expression = None
    self._user_key = 'all'
    self._end_time = None

  def _BuildAuditResource(self, credentials):
    """Builds a reports resource object to use to request logs.

    Args:
      credentials: Google API credentials

    Returns:
      A resource object for interacting with the Workspace audit API.
    """
    service = discovery.build('admin', 'reports_v1',
        credentials=credentials)
    return service

  def _GetCredentials(self):
    """Obtains API credentials for accessing the Workspace audit API.

    Returns:
      credentials: Google API credentials.
    """
    credentials = None

    # The credentials file stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    credentials_path = os.path.join(
        os.path.expanduser('~'), self._CREDENTIALS_FILENAME)
    lock = filelock.FileLock(credentials_path + '.lock')
    with lock:
      if os.path.exists(credentials_path):
        try:
          credentials = Credentials.from_authorized_user_file(
              credentials_path, self.SCOPES)
        except ValueError as exception:
          self.logger.warning(
              'Unable to load credentials: {0:s}'.format(exception))
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
          credentials = flow.run_console()

        # Save the credentials for the next run
        with open(credentials_path, 'w') as token_file:
          token_file.write(credentials.to_json())

    return credentials

  # pylint: disable=arguments-differ
  def SetUp(self, application_name, filter_expression, user_key='all',
      start_time=None, end_time=None):
    """Sets up a a Workspace Audit logs collector.

    Args:
      application_name (str): name of the application to fetch logs for. See
          https://developers.google.com/admin-sdk/reports/reference/rest/v1
          /activities/list#ApplicationName
      filter_expression (str): Workspace logs filter expression.
      user_key (Optional[str]): profile ID or email for which data should be
          collected. Can be 'all' for all users.
      start_time (Optional[str]): Beginning of the time period to return results
          for.
      end_time (Optional[str]): End of the time period to return results for.
    """
    self._credentials = self._GetCredentials()
    self._application_name = application_name
    self._filter_expression = filter_expression
    self._user_key = user_key
    self._start_time = start_time
    self._end_time = end_time

  def Process(self):
    """Copies audit logs from a Google Workspace log."""
    output_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, encoding='utf-8', suffix='.jsonl')
    output_path = output_file.name
    self.logger.info('Downloading logs to {0:s}'.format(output_path))

    audit_resource = self._BuildAuditResource(self._credentials)
    request_parameters = {
        'userKey': self._user_key,
        'applicationName': self._application_name
    }
    if self._filter_expression:
      request_parameters['filters'] = self._filter_expression
    if self._start_time:
      request_parameters['startTime'] = self._start_time
    if self._end_time:
      request_parameters['endTime'] = self._end_time

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
      self.ModuleError(exception, critical=True)

    logs_report = containers.WorkspaceLogs(
        application_name=self._application_name, path=output_path,
        filter_expression=self._filter_expression)
    self.state.StoreContainer(logs_report)


modules_manager.ModulesManager.RegisterModule(WorkspaceAuditCollector)
