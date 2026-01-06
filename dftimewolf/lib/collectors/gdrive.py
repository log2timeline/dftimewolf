# -*- coding: utf-8 -*-
"""Downloads files from Google Drive.

  This module handles the interaction with the Google Drive API to download
  files from a specified folder or by Drive file IDs.
"""

import os.path
import tempfile
from typing import Any, Optional

from concurrent import futures
from google.auth import exceptions as googleauth_exceptions
from google.oauth2.credentials import Credentials
from googleapiclient import discovery
from googleapiclient import errors as googleapi_errors
from googleapiclient.http import MediaIoBaseDownload

from dftimewolf.lib import auth
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


def ListDriveFolder(
    drive_resource: discovery.Resource,
    folder_id: str,
    fields: str,
    recursive: bool = False,
) -> list[dict[str, Any]]:
  """Lists files in a Google Drive folder.

  Args:
    drive_resource (Credentials): Google Drive API resource.
    folder_id (str): ID of the folder to list files from.
    fields (str): Fields to return in the response.
    recursive (bool): Whether to list files recursively from subfolders.

  Returns:
    list[dict[str, Any]]: List of files in the folder.
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
    self._fields: str = "nextPageToken, files"
    self._max_download_workers: int = 1
    self._overwrite_existing: bool = False

  # pylint: disable=arguments-differ
  def SetUp(
      self,
      folder_id: str,
      recursive: bool,
      drive_ids: str,
      max_download_workers: int,
      output_directory: str | None = None,
      overwrite_existing: bool = False,
  ) -> None:
    """Sets up the Google Drive Collector module.

    Args:
      folder_id (str): ID of the folder in Google Drive to download files
          from.
      recursive (bool): Whether to download files recursively from subfolders.
      drive_ids (str): Comma-separated list of file IDs to download. Duplicate
          IDs are removed.
      max_download_workers (int): Maximum number of workers to use for
          downloading files.
      output_directory (str | None): Directory to save downloaded files.
          Defaults to a temporary directory.
      overwrite_existing (bool): Whether to overwrite existing files.

    Raises:
      ModuleError: If neither folder_id nor drive_ids are specified, or if
          both are provided.
    """
    if int(max_download_workers) < 1:
      self.ModuleError(
          "max_download_workers must be at least 1.", critical=True
      )
    self._max_download_workers = int(max_download_workers)
    self._overwrite_existing = overwrite_existing

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

    if folder_id:
      self._folder_id = folder_id
      self._recursive = recursive

    if drive_ids:
      self._drive_ids = [
          drive_id for drive_id in drive_ids.split(",") if drive_id
      ]

  def _FilterDriveFiles(
      self, drive_files: list[dict[str, Any]]
  ) -> list[tuple[str, str]]:
    """Filters out non-downloadable files and folders.

    Args:
      drive_files: List of files to filter.

    Returns:
      List of tuples containing the drive ID and output path. The output path
      is the path where the file will be downloaded and is built from the
      output directory drive ID and file name.
    """
    drive_ids_and_names = []
    for drive_file in drive_files:
      drive_id = drive_file.get("id")
      if not drive_id:
        self.logger.info(f"Skipping file with no ID: {drive_file}")
        continue

      drive_name = drive_file.get("name")
      if drive_file.get("mimeType") == "application/vnd.google-apps.folder":
        self.logger.info(f"Skipping folder: {drive_name} ({drive_id})")
        continue
      if drive_file.get("mimeType", "").startswith(
          "application/vnd.google-apps."
      ):
        self.logger.info(
            f"Skipping Google Workspace native file: {drive_name} ({drive_id})"
        )
        continue
      drive_ids_and_names.append(
          (
              drive_id,
              os.path.join(
                  self._output_directory,
                  f"{drive_id}_{drive_name}",
              ),
          )
      )
    return drive_ids_and_names

  def Process(self) -> None:
    """Downloads the Drive Files or Folder to File containers."""
    drive_resource = discovery.build(
        "drive", "v3", credentials=self._credentials
    )
    drive_files = []
    if self._drive_ids:
      drive_files.extend(
          [
              drive_resource.files().get(fileId=drive_id).execute()
              for drive_id in self._drive_ids
          ]
      )

    if self._folder_id:
      drive_files.extend(
          ListDriveFolder(
              drive_resource,
              folder_id=self._folder_id,
              fields=self._fields,
              recursive=self._recursive,
          )
      )

    drive_ids_and_names = self._FilterDriveFiles(drive_files)

    with futures.ThreadPoolExecutor(
        max_workers=self._max_download_workers
    ) as executor:
      future_to_drive_id_path = {
          executor.submit(
              self._DownloadFile,
              drive_id,
              output_path,
          ): (drive_id, output_path)
          for drive_id, output_path in drive_ids_and_names
      }
      for future in futures.as_completed(future_to_drive_id_path):
        drive_id, output_path = future_to_drive_id_path[future]
        try:
          if future.result():
            self.StoreContainer(
                container=containers.File(
                    name=drive_id, path=output_path, description=""
                )
            )
        except Exception as exc:  # pylint: disable=broad-except
          self.logger.error(
              f"Download for {drive_id} generated an exception: {exc}"
          )

  def _DownloadFile(self, drive_id: str, output_file: str) -> bool:
    """Downloads a file from Google Drive.

    Args:
        drive_id (str): ID of the file to download.
        output_file (str): Path to save the downloaded file.

    Returns:
        bool: True if the file was downloaded successfully, False otherwise.
    """
    if os.path.exists(output_file) and not self._overwrite_existing:
      self.logger.warning(
          f"File {output_file} already exists, not re-downloading."
      )
      return True

    self.logger.info(f"Downloading drive ID {drive_id} to {output_file}")
    try:
      with open(output_file, "wb") as out_file:
        drive_resource = discovery.build(
            "drive", "v3", credentials=self._credentials
        )
        request = drive_resource.files().get_media(fileId=drive_id)
        downloader = MediaIoBaseDownload(out_file, request)
        done = False
        while not done:
          status, done = downloader.next_chunk(num_retries=3)
          self.logger.debug(
              f"Downloading {drive_id}: {int(status.progress() * 100)}%."
          )
        out_file.flush()
        return True

    except (
        googleapi_errors.HttpError,
        googleauth_exceptions.MutualTLSChannelError,
    ) as error:
      self.ModuleError(
          f"Failed to download drive ID {drive_id}: {error}", critical=True
      )
      if os.path.exists(output_file):
        os.remove(output_file)
      return False


modules_manager.ModulesManager.RegisterModule(GoogleDriveCollector)
