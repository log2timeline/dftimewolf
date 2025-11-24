#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Google Drive exporter."""

import unittest
from unittest import mock

from dftimewolf.lib.exporters import gdrive
from dftimewolf.lib.containers import containers
from tests.lib import modules_test_base


class GoogleDriveExporterTest(modules_test_base.ModuleTestBase):
  """Tests for the Google Drive exporter."""

  def setUp(self):
    self._InitModule(gdrive.GoogleDriveExporter)
    super(GoogleDriveExporterTest, self).setUp()

    self.mock_get_credentials_patcher = mock.patch(
        "dftimewolf.lib.auth.GetGoogleOauth2Credential"
    )
    self.mock_get_credentials = self.mock_get_credentials_patcher.start()
    self.mock_get_credentials.return_value = mock.Mock()

    self.mock_build_patcher = mock.patch("googleapiclient.discovery.build")
    self.mock_build = self.mock_build_patcher.start()
    self.mock_drive_service = mock.Mock()
    self.mock_build.return_value = self.mock_drive_service

  def tearDown(self):
    self.mock_get_credentials_patcher.stop()
    self.mock_build_patcher.stop()
    super(GoogleDriveExporterTest, self).tearDown()

  def testSetUp(self):
    """Tests the SetUp method."""
    self._module.SetUp(
        parent_folder_id="parent_folder_id", new_folder_name="new_folder_name"
    )
    self.assertEqual(self._module.parent_folder_id, "parent_folder_id")
    self.assertEqual(self._module.new_folder_name, "new_folder_name")

  @mock.patch(
      "dftimewolf.lib.exporters.gdrive.GoogleDriveExporter.CreateFolderInDrive"
  )
  @mock.patch(
      "dftimewolf.lib.exporters.gdrive.GoogleDriveExporter.UploadFileToDrive"
  )
  def testProcess(self, mock_upload_file_to_drive, mock_create_folder_in_drive):
    """Tests the Process method."""
    self._module.SetUp(
        parent_folder_id="parent_folder_id", new_folder_name="new_folder_name"
    )

    mock_create_folder_in_drive.return_value = {"id": "new_folder_id"}

    file_container = containers.File(
        name="test_file", path="/path/to/test_file"
    )
    self._module.StoreContainer(file_container)

    self._module.Process()

    mock_create_folder_in_drive.assert_called_once_with(
        self.mock_drive_service, "parent_folder_id", "new_folder_name"
    )
    mock_upload_file_to_drive.assert_called_once_with(
        folder_id="new_folder_id",
        file_name="test_file",
        file_path="/path/to/test_file",
    )

  def testCreateFolderInDrive(self):
    """Tests the CreateFolderInDrive method."""
    self._module._drive_resource = self.mock_drive_service

    self.mock_drive_service.files.return_value.create.return_value.execute.return_value = {
        "id": "folder_id",
        "name": "folder_name",
    }

    folder_metadata = self._module.CreateFolderInDrive(
        self.mock_drive_service, "parent_folder_id", "folder_name"
    )

    self.assertEqual(folder_metadata["id"], "folder_id")
    self.assertEqual(folder_metadata["name"], "folder_name")

  @mock.patch("io.FileIO")
  def testUploadFileToDrive(self, mock_file_io):
    """Tests the UploadFileToDrive method."""
    self._module._drive_resource = self.mock_drive_service

    self.mock_drive_service.files.return_value.create.return_value.execute.return_value = {
        "id": "file_id",
        "name": "file_name",
    }

    file_metadata = self._module.UploadFileToDrive(
        folder_id="folder_id", file_path="/path/to/file", file_name="file_name"
    )

    self.assertEqual(file_metadata["id"], "file_id")
    self.assertEqual(file_metadata["name"], "file_name")


if __name__ == "__main__":
  unittest.main()
