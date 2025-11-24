#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Google Drive collector."""

import unittest
from unittest import mock

from dftimewolf.lib.collectors import gdrive
from dftimewolf.lib.containers import containers
from dftimewolf.lib.state import DFTimewolfState
from tests.lib import modules_test_base


class GoogleDriveCollectorTest(modules_test_base.ModuleTestBase):
  """Tests for the Google Drive collector."""

  def setUp(self):
    self._InitModule(gdrive.GoogleDriveCollector)
    super(GoogleDriveCollectorTest, self).setUp()

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
    super(GoogleDriveCollectorTest, self).tearDown()

  def testSetUp(self):
    """Tests the SetUp method."""
    # Test with folder_id
    self._module.SetUp(
        folder_id="folder_id",
        recursive=False,
        drive_ids=None,
        output_directory=None,
    )
    self.assertEqual(self._module._folder_id, "folder_id")
    self.assertFalse(self._module._recursive)
    self.assertEqual(self._module._drive_ids, [])

    # Reset module
    self._InitModule(gdrive.GoogleDriveCollector)

    # Test with drive_ids
    self._module.SetUp(
        folder_id=None,
        recursive=False,
        drive_ids="id1,id2",
        output_directory=None,
    )
    self.assertEqual(self._module._drive_ids, ["id1", "id2"])
    self.assertEqual(self._module._folder_id, "")

    # Reset module
    self._InitModule(gdrive.GoogleDriveCollector)

    # Test with output_directory
    self._module.SetUp(
        folder_id="folder_id",
        recursive=False,
        drive_ids=None,
        output_directory="/tmp/output",
    )
    self.assertEqual(self._module._output_directory, "/tmp/output")

  @mock.patch(
      "dftimewolf.lib.collectors.gdrive.GoogleDriveCollector._DownloadFile"
  )
  @mock.patch("dftimewolf.lib.collectors.gdrive.ListDriveFolder")
  def testProcess(self, mock_list_drive_folder, mock_download_file):
    """Tests the Process method."""

    # Test with folder_id
    self._module.SetUp(
        folder_id="folder_id",
        recursive=False,
        drive_ids=None,
        output_directory=None,
    )

    mock_list_drive_folder.return_value = [
        {"id": "file1", "name": "file1.txt"},
        {"id": "file2", "name": "file2.txt"},
    ]
    mock_download_file.return_value = "/tmp/output/file.txt"

    self._module.Process()

    mock_list_drive_folder.assert_called_with(
        self.mock_drive_service,
        folder_id="folder_id",
        fields="nextPageToken, files",
        recursive=False,
    )
    self.assertEqual(mock_download_file.call_count, 2)
    self.assertEqual(
        len(
            self._module.state.GetContainers(self._module.name, containers.File)
        ),
        2,
    )

    # Reset for drive_ids test
    self._InitModule(gdrive.GoogleDriveCollector)
    mock_download_file.reset_mock()

    # Test with drive_ids
    self._module.SetUp(
        folder_id=None,
        recursive=False,
        drive_ids="id3,id4",
        output_directory=None,
    )

    self._module.Process()

    self.assertEqual(mock_download_file.call_count, 2)
    self.assertEqual(
        len(
            self._module.state.GetContainers(self._module.name, containers.File)
        ),
        2,
    )

  def testListDriveFolder(self):
    """Tests the ListDriveFolder function."""
    mock_drive_resource = mock.Mock()
    mock_files = mock_drive_resource.files.return_value
    mock_list = mock_files.list.return_value

    # Mock response with pagination
    mock_list.execute.side_effect = [
        {
            "files": [
                {"id": "file1", "name": "file1", "mimeType": "text/plain"}
            ],
            "nextPageToken": "token",
        },
        {"files": [{"id": "file2", "name": "file2", "mimeType": "text/plain"}]},
    ]

    files = gdrive.ListDriveFolder(
        mock_drive_resource,
        folder_id="folder_id",
        fields="fields",
        recursive=False,
    )

    self.assertEqual(len(files), 2)
    self.assertEqual(files[0]["id"], "file1")
    self.assertEqual(files[1]["id"], "file2")

    # Verify calls
    self.assertEqual(mock_list.execute.call_count, 2)

    # Test recursive
    mock_list.execute.side_effect = [
        {
            "files": [
                {
                    "id": "folder1",
                    "name": "folder1",
                    "mimeType": "application/vnd.google-apps.folder",
                },
                {"id": "file3", "name": "file3", "mimeType": "text/plain"},
            ]
        },
        {"files": [{"id": "file4", "name": "file4", "mimeType": "text/plain"}]},
    ]

    files = gdrive.ListDriveFolder(
        mock_drive_resource,
        folder_id="folder_id",
        fields="fields",
        recursive=True,
    )

    self.assertEqual(len(files), 3)
    ids = [f["id"] for f in files]
    self.assertIn("folder1", ids)
    self.assertIn("file3", ids)
    self.assertIn("file4", ids)


if __name__ == "__main__":
  unittest.main()
