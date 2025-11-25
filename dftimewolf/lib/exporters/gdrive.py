# -*- coding: utf-8 -*-
"""Uploads files to Google Drive.

This module handles the authentication and interaction with the Google Drive API
to upload files to a specified folder.
"""

import io
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from googleapiclient import discovery
from googleapiclient import errors as googleapi_errors
from googleapiclient.http import MediaIoBaseUpload

from dftimewolf.lib import auth
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class GoogleDriveExporter(module.BaseModule):
  """Exporter for files to Google Drive."""

  SCOPES = [
      "https://www.googleapis.com/auth/drive",
  ]
  _CREDENTIALS_FILENAME = ".dftimewolf_drive_export_credentials.json"
  _CLIENT_SECRET_FILENAME = ".dftimewolf_drive_client_secret.json"

  def __init__(
      self,
      state: DFTimewolfState,
      name: Optional[str] = None,
      critical: bool = False,
  ) -> None:
    """Initializes a Google Drive collector."""
    super(GoogleDriveExporter, self).__init__(
        state, name=name, critical=critical
    )
    self.parent_folder_id: Optional[str] = None
    self.new_folder_name: Optional[str] = None
    self._credentials: Optional[Credentials] = None
    self._drive_resource = None

  # pylint: disable=arguments-differ
  def SetUp(self, parent_folder_id: str, new_folder_name: str) -> None:
    """Sets up the Google Drive Exporter module.

    Args:
        parent_folder_id (str): ID of the parent folder in Google Drive.
        new_folder_name (str): Name of the new folder to create in the parent
            folder.

    Raises:
        ModuleError: If the parent folder ID is not specified.
    """
    if not parent_folder_id:
      self.ModuleError("Specify a parent folder id.", critical=True)

    self.parent_folder_id = parent_folder_id
    self.new_folder_name = new_folder_name

    self._credentials = auth.GetGoogleOauth2Credential(
        scopes=self.SCOPES,
        credential_path=self._CREDENTIALS_FILENAME,
        secret_path=self._CLIENT_SECRET_FILENAME,
    )
    self._drive_resource = discovery.build(
        "drive", "v3", credentials=self._credentials
    )

  def Process(self) -> None:
    """Processes the files and uploads them to Google Drive.

    Raises:
        ModuleError: If the Drive resource is not initialized.
    """
    if not self._drive_resource:
      self.ModuleError("Drive Resource not initialized.", critical=True)

    folder_id = self.parent_folder_id
    if self.new_folder_name:
      new_folder = self.CreateFolderInDrive(
          self._drive_resource,
          self.parent_folder_id,  # type: ignore[arg-type]
          self.new_folder_name
      )
      folder_id = new_folder["id"]

    self.logger.info(f"Uploading to folder ID {folder_id}")
    for file_container in self.GetContainers(containers.File):
      self.UploadFileToDrive(
          folder_id=folder_id,  # type: ignore[arg-type]
          file_name=file_container.name,
          file_path=file_container.path,
      )

  def CreateFolderInDrive(
      self, drive_resource: Credentials, parent_folder_id: str, folder_name: str
  ) -> Any:
    """Creates a folder in Google Drive under a specific parent folder.

    Args:
        drive_resource: Authorized Google Drive API resource.
        parent_folder_id (str): ID of the parent folder where the new folder
            will be created.
        folder_name (str): Name of the new folder to create.

    Returns:
        dict: The metadata of the created folder.

    Raises:
        ModuleError: If the folder creation fails.
    """
    try:
      # pylint: disable=maybe-no-member
      created_folder = (
          drive_resource.files()
          .create(
              body={
                  "name": folder_name,
                  "mimeType": "application/vnd.google-apps.folder",
                  "parents": [parent_folder_id],
              },
              fields="id, name, mimeType, parents",
          )
          .execute()
      )
      self.logger.info(
          f"Created folder: {created_folder.get('name')} "
          f"(ID: {created_folder.get('id')})"
      )
      return created_folder
    except googleapi_errors.HttpError as error:
      self.ModuleError(f"Could not create folder {folder_name}: {error}")
      return None

  def UploadFileToDrive(
      self, folder_id: str, file_path: str, file_name: Optional[str] = None
  ) -> Any:
    """Uploads a file to Google Drive into a specific folder.

    Args:
        folder_id (str): ID of the folder to upload the file to.
        file_path (str): Path to the file to upload.
        file_name (str, optional): Name for the uploaded file. Defaults to the
            original file name.

    Returns:
        dict: The metadata of the uploaded file.

    Raises:
        ModuleError: If the file upload fails.
    """
    try:
      # pylint: disable=maybe-no-member
      uploaded_file = (
          self._drive_resource.files()  # type: ignore[attr-defined]
          .create(
              body={
                  "name": file_name,
                  "parents": [folder_id],
              },
              media_body=MediaIoBaseUpload(
                  io.FileIO(file_path, "rb"),
                  mimetype="application/octet-stream",
                  resumable=True,
              ),
              fields="id, name, mimeType, parents",
          )
          .execute()
      )
      self.logger.info(
          f"Uploaded file: {uploaded_file.get('name')} "
          f"(ID: {uploaded_file.get('id')})"
      )
      return uploaded_file
    except googleapi_errors.HttpError as error:
      self.ModuleError(
          f"Error while uploading {file_name} ({file_path}): {error}",
          critical=True,
      )
      return None


modules_manager.ModulesManager.RegisterModule(GoogleDriveExporter)
