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

  # For pytype
  _module: gdrive.GoogleDriveExporter

  def setUp(self):
    # pylint: disable=protected-access
    self._InitModule(gdrive.GoogleDriveExporter)
    super().setUp()

    self.mock_get_credentials_patcher = mock.patch(
        "dftimewolf.lib.auth.GetGoogleOauth2Credential"
    )
    self.mock_get_credentials = self.mock_get_credentials_patcher.start()
    self.mock_get_credentials.return_value = mock.Mock()

    self.mock_build_patcher = mock.patch("googleapiclient.discovery.build")
    self.mock_build = self.mock_build_patcher.start()
    self.mock_drive_service = mock.Mock()
    self.mock_build.return_value = self.mock_drive_service

    self.mock_file_io_patcher = mock.patch("io.FileIO")
    self.mock_file_io = self.mock_file_io_patcher.start()

  def tearDown(self):
    self.mock_get_credentials_patcher.stop()
    self.mock_build_patcher.stop()
    self.mock_file_io_patcher.stop()
    super().tearDown()

  def testSetUp(self):
    """Tests the SetUp method."""
    self._module.SetUp(
        parent_folder_id="parent_folder_id",
        new_folder_name="new_folder_name",
        max_upload_workers=5,
    )
    # pylint: disable=protected-access
    self.assertEqual(self._module.parent_folder_id, "parent_folder_id")
    self.assertEqual(self._module.new_folder_name, "new_folder_name")
    self.assertEqual(self._module._max_upload_workers, 5)

  def testProcess(self):
    """Tests the Process method."""
    # pylint: disable=protected-access
    self._module.SetUp(
        parent_folder_id="parent_folder_id",
        new_folder_name="new_folder_name",
        max_upload_workers=5,
    )

    self.mock_drive_service.files.return_value.create.return_value.execute.side_effect = [  # pylint: disable=line-too-long
        {"id": "new_folder_id", "name": "new_folder_name"},
        {"id": "file_id", "name": "test_file"},
    ]

    file_container = containers.File(
        name="test_file", path="/path/to/test_file"
    )
    self._module.StoreContainer(file_container)

    self._ProcessModule()

    self.mock_drive_service.files.return_value.create.assert_any_call(
        body={
            "name": "new_folder_name",
            "mimeType": "application/vnd.google-apps.folder",
            "parents": ["parent_folder_id"],
        },
        fields="id, name, mimeType, parents",
    )

    self.mock_drive_service.files.return_value.create.assert_any_call(
        body={
            "name": "test_file",
            "parents": ["new_folder_id"],
        },
        media_body=mock.ANY,
        fields="id, name, mimeType, parents",
    )


if __name__ == "__main__":
  unittest.main()
