# -*- coding: utf-8 -*-
"""Uploads files to Google Drive.

This module handles the authentication and interaction with the Google Drive API
to upload files to a specified folder.
"""

import io
from typing import Any, Optional, Type, cast

from google.auth import exceptions as googleauth_exceptions
from google.oauth2.credentials import Credentials
from googleapiclient import discovery
from googleapiclient import errors as googleapi_errors
from googleapiclient.http import MediaIoBaseUpload
from dftimewolf.lib import auth
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class GoogleDriveExporter(module.ThreadAwareModule):
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
    self.folder_id: Optional[str] = None
    self.new_folder_name: Optional[str] = None
    self._credentials: Optional[Credentials] = None
    self._drive_resource: Optional[discovery.Resource] = None
    self._max_upload_workers: Optional[int] = None

  # pylint: disable=arguments-differ
  def SetUp(
      self, parent_folder_id: str, new_folder_name: str, max_upload_workers: int
  ) -> None:
    """Sets up the Google Drive Exporter module.

    Args:
        parent_folder_id (str): ID of the parent folder in Google Drive.
        new_folder_name (str): Name of the new folder to create in the parent
            folder.
        max_upload_workers (int): Maximum number of upload workers.

    Raises:
        ModuleError: If the parent folder ID is not specified.
    """
    if max_upload_workers < 1:
      self.ModuleError("Specify a valid max upload workers.", critical=True)
    self._max_upload_workers = max_upload_workers

    if not parent_folder_id:
      self.ModuleError("Specify a parent folder id.", critical=True)

    self.parent_folder_id = parent_folder_id
    self.new_folder_name = new_folder_name

    self._credentials = auth.GetGoogleOauth2Credential(
        scopes=self.SCOPES,
        credential_path=self._CREDENTIALS_FILENAME,
        secret_path=self._CLIENT_SECRET_FILENAME,
    )

  def PreProcess(self) -> None:
    """Preprocesses the files and uploads them to Google Drive."""
    if self.new_folder_name:
      new_folder = self.CreateFolderInDrive(
          self.parent_folder_id,  # type: ignore[arg-type]
          self.new_folder_name,
      )
      self.folder_id = new_folder["id"]
    else:
      self.folder_id = self.parent_folder_id

  def Process(self, container: interface.AttributeContainer) -> None:
    """Processes the files and uploads them to Google Drive.

    Raises:
        ModuleError: If the Drive resource is not initialized.
    """
    container = cast(containers.File, container)
    self.logger.info(f"Uploading to folder ID {self.folder_id}")
    try:
      drive_resource = discovery.build(
          "drive", "v3", credentials=self._credentials
      )
      uploaded_file = (
          drive_resource.files()
          .create(
              body={
                  "name": container.name,
                  "parents": [self.folder_id],
              },
              media_body=MediaIoBaseUpload(
                  io.FileIO(container.path, "rb"),
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
    except (
        googleapi_errors.HttpError,
        googleauth_exceptions.MutualTLSChannelError,
    ) as error:
      self.ModuleError(
          f"Error while uploading {container.name} ({container.path}): {error}",
          critical=True,
      )
      return None

  def CreateFolderInDrive(self, parent_folder_id: str, folder_name: str) -> Any:
    """Creates a folder in Google Drive under a specific parent folder.

    Args:
        parent_folder_id (str): ID of the parent folder where the new folder
            will be created.
        folder_name (str): Name of the new folder to create.

    Returns:
        dict: The metadata of the created folder.

    Raises:
        ModuleError: If the folder creation fails.
    """
    try:
      drive_resource = discovery.build(
          "drive", "v3", credentials=self._credentials
      )
      created_folder = (
          drive_resource.files()  # type: ignore[attr-defined]
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
    except (
        googleapi_errors.HttpError,
        googleauth_exceptions.MutualTLSChannelError,
    ) as error:
      self.ModuleError(f"Could not create folder {folder_name}: {error}")
      return None

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    """Returns the container type that this module should be threaded on."""
    return containers.File

  def GetThreadPoolSize(self) -> int:
    """Returns the maximum number of threads for this module."""
    return self._max_upload_workers or 5

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(GoogleDriveExporter)
