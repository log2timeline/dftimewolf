# -*- coding: utf-8 -*-
"""Pulls entries from Google Sheets."""

import os.path
import re
import tempfile
from typing import List
from typing import Optional

import filelock
import pandas as pd
from google.auth.exceptions import DefaultCredentialsError
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class GoogleSheetsCollector(module.BaseModule):
  """Collector for entries from Google Sheets."""

  SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

  _CREDENTIALS_FILENAME = '.dftimewolf_google_sheets_credentials.json'
  _CLIENT_SECRET_FILENAME = '.dftimewolf_google_sheets_client_secret.json'

  def __init__(
      self,
      state: DFTimewolfState,
      name: Optional[str] = None,
      critical: bool = False) -> None:
    """Initializes a Google Sheets collector."""
    super(GoogleSheetsCollector, self).__init__(
        state, name=name, critical=critical)
    self._sheets_resource = None
    self._credentials = None
    self._spreadsheet_id = ''
    self._sheet_names: List[str] = []
    # These are mandatory columns required by Timesketch.
    self._mandatory_columns = ['message', 'datetime', 'timestamp_desc']
    self._all_sheets = False
    self._validate_columns = True

  # pylint: disable=arguments-differ
  def SetUp(
      self, spreadsheet: str, sheet_names: List[str],
      validate_columns: bool) -> None:
    """Sets up a a Google Sheets collector.

    Args:
      spreadsheet: ID or URL of the sheet to pull data from
      sheet_names: List of sheet names inside the spreadsheet to parse. If not
        set, all sheets inside the spreadsheet will be parsed.
      validate_columns: Check if mandatory columns required by Timesketch is
        present in the sheets.
    """
    self._credentials = self._GetCredentials()
    self._spreadsheet_id = self._ValidateSpreadSheetId(spreadsheet)
    self._sheet_names = sheet_names
    if not sheet_names:
      self._all_sheets = True
    self._validate_columns = validate_columns
    self._sheets_resource = discovery.build(
        'sheets', 'v4', credentials=self._credentials)

  def Process(self) -> None:
    """Copies entries from Google Sheets."""

    try:
      if not self._sheets_resource:
        self.ModuleError(
            'Google Sheets API resource was not initialized', critical=True)
        return  #return is required otherwise mypy will complain

      # Retrieve list of sheets in the spreadsheet
      # Pylint can't see the spreadsheets method.
      # pylint: disable=no-member
      result = self._sheets_resource.spreadsheets().get(
          spreadsheetId=self._spreadsheet_id).execute()
      spreadsheet_title = result.get('properties', {}).get('title')
      sheets = result.get('sheets', [])

      for sheet in sheets:
        if not sheet.get('properties'):
          continue

        sheet_title = sheet.get('properties').get('title')

        if not self._all_sheets and sheet_title not in self._sheet_names:
          continue

        self.logger.debug(f"Parsing sheet: {sheet_title}")

        df = self._ExtractEntriesFromSheet(self._spreadsheet_id, sheet_title)

        if df is None or df.empty:
          continue

        output_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, encoding='utf-8', suffix='.csv')
        output_path = output_file.name
        self.logger.debug(
          f'Downloading results of sheet "{sheet_title}" to {output_path}'
        )

        df.to_csv(index=False, na_rep='NaN', path_or_buf=output_file)

        self.PublishMessage(
            f'Downloaded results of sheet "{sheet_title}" to {output_path}')
        output_file.close()
        sheet_csv_file = containers.File(
            name=self._spreadsheet_id,
            path=output_path,
            description=f'{spreadsheet_title}_{sheet_title}')
        self.StoreContainer(sheet_csv_file)

    except (RefreshError, DefaultCredentialsError) as exception:
      self.ModuleError(
          'Something is wrong with your gcloud access token or '
          'Application Default Credentials. Try running:\n '
          '$ gcloud auth application-default login')
      self.ModuleError(str(exception), critical=True)

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
          self.logger.warning(f'Unable to load credentials: {exception}')
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
                f'and save them to {secrets_path}.')
            self.ModuleError(error_message, critical=True)
          flow = InstalledAppFlow.from_client_secrets_file(
              secrets_path, self.SCOPES)
          credentials = flow.run_console()

        # Save the credentials for the next run
        with open(credentials_path, 'w') as token_file:
          token_file.write(credentials.to_json())

    return credentials

  def _ValidateSpreadSheetId(self, spreadsheet: str) -> str:
    """Extract and validate spreadsheet ID.

    Args:
      spreadsheet: ID or URL of the sheetspread,

    Returns:
      spreadsheet ID
    """
    spreadsheet_match = re.search(r'.*?([01][0-9A-Za-z_-]{20,}).*', spreadsheet)
    if not spreadsheet_match:
      self.ModuleError(
          f'spreadsheet ID is not in the correct format {spreadsheet}.',
          critical=True)
      return ""  #return is required otherwise mypy will complain

    return spreadsheet_match.group(1)

  def _ExtractEntriesFromSheet(self, spreadsheet_id: str,
                               sheet_title: str) -> Optional[pd.DataFrame]:
    """Extract entries from the sheet inside the spreadsheet.

    Args:
      spreadsheet_id: ID of the spreadsheet to pull data from
      sheet_title: Title of the sheet inside the spreadsheet to parse.

    Returns:
        Dataframe with entries from sheet inside the spreadsheet or None if the
        sheet contain no entries.
    """

    if not self._sheets_resource:
      self.ModuleError(
          'Google Sheets API resource was not initialized', critical=True)
      return None  #return is required otherwise mypy will complain

    # Pylint can't see the spreadsheets method.
    # pylint: disable=no-member
    sheet_content_result = self._sheets_resource.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=sheet_title).execute()
    values = sheet_content_result.get('values', [])

    if not values:
      self.logger.warning(f'No data found in sheet "{sheet_title}".')
      return None

    df = pd.DataFrame(values[1:], columns=values[0])
    df.replace('', 'NaN', inplace=True)
    df.fillna('NaN', inplace=True)

    # Removing white spaces from column names
    df.rename(columns=lambda name: name.strip(), inplace=True)

    if not self._validate_columns:
      return df

    for column in self._mandatory_columns:
      if column not in df.columns:
        self.logger.warning(
            f'Mandatory column "{column}" was not found in sheet \
              "{sheet_title}".')
        self.logger.warning(
            'Please make sure all mandatory columns are \
          present:')
        self.logger.warning(
            '"message": String with an informative message of the event')
        self.logger.warning(
            '"datetime": ISO8601 format for example: 2015-07-24T19:01:01+00:00')
        self.logger.warning(
            '"timestamp_desc": String explaining what type of timestamp it is \
              for example file created')
        return None
    return df


modules_manager.ModulesManager.RegisterModule(GoogleSheetsCollector)
