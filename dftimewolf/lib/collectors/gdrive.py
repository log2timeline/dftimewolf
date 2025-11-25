# -*- coding: utf-8 -*-
"""Downloads files from Google Drive.

  This module handles the authentication and interaction with the Google Drive
  API to download files from a specified folder or by file IDs.
"""

import os.path
import tempfile
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient import discovery
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from dftimewolf.lib import auth
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


def ListDriveFolder(
    drive_resource: Credentials,
    folder_id: str,
    fields: str,
    recursive: bool = False,
) -> list[discovery.Resource]:
  """Lists files in a Google Drive folder.

  Args:
    drive_resource (Credentials): Google Drive API resource.
    folder_id (str): ID of the folder to list files from.
    fields (str): Fields to return in the response.
    recursive (bool): Whether to list files recursively from subfolders.

  Returns:
    list[discovery.Resource]: List of files in the folder.
  """
  files = []
  page_token = None
  query = f"'{folder_id}' in parents and trashed = false"
  while True:
    # pylint: disable=maybe-no-member
    response = (
        drive_resource.files()
        .list(
            q=query,
            spaces="drive",
            fields=fields,
            pageToken=page_token,
        )
        .execute()
    )

    for file in response.get("files", []):
      files.append(file)
      if (
          recursive
          and file.get("mimeType") == "application/vnd.google-apps.folder"
      ):
        files.extend(
            ListDriveFolder(drive_resource, file.get("id"), fields, recursive)
        )

    page_token = response.get("nextPageToken", None)
    if page_token is None:
      break
  return files


class GoogleDriveCollector(module.BaseModule):
  """Collector for files and folders from Google Drive."""

  SCOPES = [
      "https://www.googleapis.com/auth/drive.readonly",
      "https://www.googleapis.com/auth/drive.metadata.readonly",
  ]
  _CREDENTIALS_FILENAME = ".dftimewolf_drive_collect_credentials.json"
  _CLIENT_SECRET_FILENAME = ".dftimewolf_drive_client_secret.json"

  def __init__(
      self,
      state: DFTimewolfState,
      name: Optional[str] = None,
      critical: bool = False,
  ) -> None:
    """Initializes a Google Drive collector."""
    super(GoogleDriveCollector, self).__init__(
        state, name=name, critical=critical
    )
    self._credentials: Optional[Credentials] = None
    self._drive_ids: list[str] = []
    self._folder_id: str = ""
    self._output_directory: str = ""
    self._recursive: bool = False
    self._drive_resource = None
    self._fields = "nextPageToken, files"

  # pylint: disable=arguments-differ
  def SetUp(
      self,
      folder_id: str,
      recursive: bool,
      drive_ids: str,
      output_directory: str | None,
  ) -> None:
    """Sets up the Google Drive Collector module.

    Args:
        folder_id (str): ID of the folder in Google Drive to download files
          from.
        recursive (bool): Whether to download files recursively from subfolders.
        drive_ids (str): Comma-separated list of file IDs to download.
        output_directory (str | None): Directory to save downloaded files.
          Defaults to a temporary directory.

    Raises:
        ModuleError: If neither folder_id nor drive_ids are specified, or if
          both are provided.
    """
    if not folder_id and not drive_ids:
      self.ModuleError(
          "Specify either folder_id or drive_ids argument.", critical=True
      )

    if folder_id and drive_ids:
      self.ModuleError(
          "folder_id and drive_ids are mutually exclusive", critical=True
      )

    if not output_directory:
      self._output_directory = tempfile.mkdtemp(
          prefix="dftimewolf_gdrive_collect"
      )
    else:
      if os.path.exists(output_directory):
        if not os.path.isdir(output_directory):
          self.ModuleError(
              f"{output_directory} exists but is not a directory.",
              critical=True,
          )
        if os.listdir(output_directory):
          self.ModuleError(
              f"{output_directory} exists but is not empty.", critical=True
          )
      else:
        os.makedirs(output_directory)
      self._output_directory = output_directory

    self._credentials = auth.GetGoogleOauth2Credential(
        scopes=self.SCOPES,
        credential_path=self._CREDENTIALS_FILENAME,
        secret_path=self._CLIENT_SECRET_FILENAME,
    )
    self._drive_resource = discovery.build(
        "drive", "v3", credentials=self._credentials
    )

    if folder_id:
      self._folder_id = folder_id
      self._recursive = recursive

    if drive_ids:
      self._drive_ids = [
          drive_id for drive_id in drive_ids.split(",") if drive_id
      ]

  def Process(self) -> None:
    """Processes the files and downloads them from Google Drive.

    Raises:
        ModuleError: If the Drive resource is not initialized.
    """
    if not self._drive_resource:
      self.ModuleError("Drive Resource not initialized.", critical=True)

    files = []
    if self._folder_id:
      for drive_file in ListDriveFolder(
          self._drive_resource,
          folder_id=self._folder_id,
          fields=self._fields,
          recursive=self._recursive,
      ):
        # Skip folders and Google Workspace native files.
        mime_type = drive_file.get("mimeType")
        if mime_type == "application/vnd.google-apps.folder":
          self.logger.info(
              f'Skipping folder: {drive_file.get("name")} '
              f'({drive_file.get("id")})'
          )
          continue
        if mime_type and mime_type.startswith("application/vnd.google-apps."):
          self.logger.info(
              f"Skipping Google Workspace native file: "
              f'{drive_file.get("name")} '
              f'({drive_file.get("id")}) with mimeType: {mime_type}. '
          )
          continue

        self.logger.info(
            f'Found downloadable file: {drive_file.get("name")}, '
            f'{drive_file.get("id")}'
        )
        files.append(drive_file)
      for file in files:
        drive_file_id = file.get("id")
        drive_file_name = file.get("name")
        file_name = os.path.join(
            self._output_directory, f"{drive_file_id}_{drive_file_name}"
        )
        self._DownloadFile(drive_file_id, file_name)
        self.StoreContainer(
            container=containers.File(
                name=drive_file_id, path=file_name, description=""
            )
        )

    if self._drive_ids:
      for drive_id in self._drive_ids:
        file_name = os.path.join(self._output_directory, drive_id)
        self._DownloadFile(drive_id, file_name)
        self.StoreContainer(
            container=containers.File(
                name=drive_id, path=file_name, description=""
            )
        )

  def _DownloadFile(self, drive_id: str, output_file: str) -> bool:
    """Downloads a file from Google Drive.

    Args:
        drive_id (str): ID of the file to download.
        output_file (str): Path to save the downloaded file.

    Returns:
        bool: True if the file was downloaded successfully, False otherwise.
    """
    self.logger.info(f"Downloading drive ID {drive_id} to {output_file}")
    with open(output_file, "wb") as out_file:
      try:
        # pylint: disable=maybe-no-member
        request = self._drive_resource.files().get_media(fileId=drive_id)  # type: ignore[attr-defined]  # pylint: disable=line-too-long
        downloader = MediaIoBaseDownload(out_file, request)
        done = False
        while done is False:
          status, done = downloader.next_chunk()
          self.logger.debug(
              f"Downloading {drive_id}: {int(status.progress() * 100)}%."
          )
        # Ensure the file is flushed and closed before returning.
        out_file.flush()
        return True

      except HttpError as error:
        self.ModuleError(
            f"Failed to download drive ID {drive_id}: {error}", critical=True
        )
        return False


modules_manager.ModulesManager.RegisterModule(GoogleDriveCollector)
