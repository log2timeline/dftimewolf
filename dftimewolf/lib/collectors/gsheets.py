# -*- coding: utf-8 -*-
"""Pulls entries from Google Sheets."""

import os.path
import re
import tempfile
from typing import List, Optional, TYPE_CHECKING

from pandas.core.frame import DataFrame

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
import filelock
from google.auth.exceptions import DefaultCredentialsError
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery
import pandas as pd

if TYPE_CHECKING:
  from dftimewolf.lib import state


class GoogleSheetsCollector(module.BaseModule):
  """Collector for entries from Google Sheets. """

  SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

  _CREDENTIALS_FILENAME = '.dftimewolf_google_sheets_credentials.json'
  _CLIENT_SECRET_FILENAME = '.dftimewolf_google_sheets_client_secret.json'

  def __init__(self,
               state: 'state.DFTimewolfState',
               name: Optional[str] = None,
               critical: bool = False) -> None:
    """Initializes a Google Sheets collector."""
    super(GoogleSheetsCollector, self).__init__(
        state, name=name, critical=critical)
    self._credentials = None
    self._spreadsheet_id = ''
    self._sheets_names = ''
    self._mandatory_columns = ['message', 'datetime', 'timestamp_desc']
    self._all_sheets = False

  # pylint: disable=arguments-differ
  def SetUp(self, spreadsheet: str, sheets_names: List[str]) -> None:
    """Sets up a a Google Sheets collector.

    Args:
      spreadsheet: ID or URL of the sheet to pull data from
      sheets_names: List of sheets names inside the spreadsheet to parse. 'All'
        will parse all sheets inside a spreadsheet.
    """
    self._credentials = self._GetCredentials()
    self._spreadsheet_id = self._ValidateSpreadSheetId(spreadsheet)
    self._sheets_names = sheets_names
    if 'All' in sheets_names:
      self._all_sheets = True

  def Process(self) -> None:
    """Copies entries from Google Sheets."""

    try:
      # Retrive list of sheets in the spreadsheet
      service = self._BuildSheetsResource(self._credentials)
      result = service.spreadsheets().get(
          spreadsheetId=self._spreadsheet_id).execute()
      spreadsheet_title = result.get('properties', {}).get('title')
      sheets = (result.get('sheets', []))

      for sheet in sheets:
        if not sheet.get('properties'):
          continue

        sheet_title = sheet.get('properties', {}).get('title')

        if not self._all_sheets and sheet_title not in self._sheets_names:
          continue

        self.logger.info('Parsing sheet: {0:s}'.format(sheet_title))

        df = self._ParseSheet(self._spreadsheet_id, sheet_title)

        if df is None or df.empty:
          continue

        output_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, encoding='utf-8', suffix='.csv')
        output_path = output_file.name
        self.logger.info(
            'Downloading results to of sheet "{0:s}" to {1:s}'.format(
                sheet_title, output_path))

        df.to_csv(index=False, na_rep='NaN', path_or_buf=output_file)

        self.logger.success(
            'Downloaded results of sheet "{0:s}" to {1:s}'.format(
                sheet_title, output_path))
        output_file.close()
        sheet_csv_file = containers.File(
            name='{0:s}_{1:s}'.format(spreadsheet_title, sheet_title),
            path=output_path)
        self.state.StoreContainer(sheet_csv_file)

    except (RefreshError, DefaultCredentialsError) as exception:
      self.ModuleError('Something is wrong with your gcloud access token or '
                       'Application Default Credentials. Try running:\n '
                       '$ gcloud auth application-default login')
      self.ModuleError(exception, critical=True)

  def _GetCredentials(self) -> Credentials:
    """Obtains API credentials for accessing the Google Sheets API.

    Returns:
      google.oauth2.credentials.Credentials: Google API credentials.
    """
    credentials = None

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
                'No OAuth application credentials available to access google '
                'sheets. Please generate OAuth application credentials (see '
                'https://developers.google.com/sheets/api/guides/authorizing) '
                'and save them to {0:s}.').format(secrets_path)
            self.ModuleError(error_message, True)
          flow = InstalledAppFlow.from_client_secrets_file(
              secrets_path, self.SCOPES)
          credentials = flow.run_console()

        # Save the credentials for the next run
        with open(credentials_path, 'w') as token_file:
          token_file.write(credentials.to_json())

    return credentials

  def _BuildSheetsResource(self, credentials: Credentials) -> discovery.Resource:
    """Builds a Google Sheets resource object to use to request logs.

    Args:
      credentials: Google API credentials

    Returns:
      A resouce object for interacting with the Google Sheets API.
    """
    resource = discovery.build('sheets', 'v4', credentials=credentials)

    return resource

  def _ValidateSpreadSheetId(self, spreadsheet: str) -> str:
    """Extract the spreadsheet id if the input is a URL and validate that the ID
    is in the correct format.

    Args:
      spreadsheet: ID or URL of the sheetspread,

    Returns:
      spreadsheet ID
    """
    spreadsheet_match = re.search(r'.*?([01][0-9A-Za-z_-]{20,}).*',
                                     spreadsheet)
    if not spreadsheet_match:
      self.ModuleError(
          'spreadsheet id is not in the correct format {0:s}.'.format(
              spreadsheet),
          critical=True)

    return spreadsheet_match.group(1)

  def _ParseSheet(self, spreadsheet_id: str, sheet_title: str) -> DataFrame:
    """Parse sheet content

      Args:
      spreadsheet_id: ID of the spreadsheet to pull data from
      sheets_title: Title of the sheet inside the spreadsheet to parse.

      Returns:
        Dataframe with entries from sheet inside the spreadsheet
    """

    df = pd.DataFrame()

    resource = self._BuildSheetsResource(self._credentials)

    sheet_content_result = resource.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=sheet_title).execute()
    values = sheet_content_result.get('values', [])

    if not values:
      self.logger.warning('No data found in sheet "{0:s}".'.format(sheet_title))
      return None

    df = pd.DataFrame(values[1:], columns=values[0])
    df.replace('', 'NaN', inplace=True)
    df.fillna('NaN', inplace=True)

    # Removing white spaces from column names
    df.rename(columns=lambda name: name.strip(), inplace=True)

    for column in self._mandatory_columns:
      if column not in df.columns:
        self.logger.error(
            'Mandatory column "{0:s}" was not found in sheet "{1:s}".'.format(
                column, sheet_title))
        self.logger.error('Please make sure all mandatory are present:')
        self.logger.error(
            '"message": String with an informative message of the event')
        self.logger.error(
            '"datetime": ISO8601 format for example: 2015-07-24T19:01:01+00:00')
        self.logger.error(
            '"timestamp_desc": String explaining what type of timestamp it is for example file created'
        )
        return None

    return df


modules_manager.ModulesManager.RegisterModule(GoogleSheetsCollector)
