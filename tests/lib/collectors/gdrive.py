#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Google Drive collector."""

import unittest
from unittest import mock

from absl.testing import parameterized

from dftimewolf.lib.collectors import gdrive
from dftimewolf.lib.containers import containers
from tests.lib import modules_test_base


class GoogleDriveCollectorTest(modules_test_base.ModuleTestBase):
  """Tests for the Google Drive collector."""

  # For pytype
  _module: gdrive.GoogleDriveCollector

  def setUp(self):
    # pylint: disable=protected-access
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

    self.mock_media_io_patcher = mock.patch(
        "dftimewolf.lib.collectors.gdrive.MediaIoBaseDownload"
    )
    self.mock_media_io = self.mock_media_io_patcher.start()
    self.mock_downloader = self.mock_media_io.return_value
    mock_status = mock.Mock()
    mock_status.progress.return_value = 1.0
    self.mock_downloader.next_chunk.return_value = (mock_status, True)

    self.mock_drive_service.files.return_value.get_media.return_value = (
        mock.Mock()
    )

  def tearDown(self):
    self.mock_get_credentials_patcher.stop()
    self.mock_build_patcher.stop()
    self.mock_media_io_patcher.stop()
    super(GoogleDriveCollectorTest, self).tearDown()

  @parameterized.named_parameters(
      ("FolderId", "folder_id", False, "", 5, None, "folder_id", False, [], 5),
      ("DriveIds", "", False, "id1,id2", 5, None, "", False, ["id1", "id2"], 5),
      (
          "OutputDirectory",
          "folder_id",
          False,
          "",
          5,
          "/tmp/output",
          "folder_id",
          False,
          [],
          5,
      ),
  )
  def testSetUp(
      self,
      folder_id,
      recursive,
      drive_ids,
      max_download_workers,
      output_directory,
      expected_folder_id,
      expected_recursive,
      expected_drive_ids,
      expected_max_download_workers,
  ):
    """Tests the SetUp method."""
    # pylint: disable=protected-access
    self._module.SetUp(
        folder_id=folder_id,
        recursive=recursive,
        drive_ids=drive_ids,
        max_download_workers=max_download_workers,
        output_directory=output_directory,
    )
    self.assertEqual(self._module._folder_id, expected_folder_id)
    self.assertEqual(self._module._recursive, expected_recursive)
    self.assertSameElements(self._module._drive_ids, expected_drive_ids)
    self.assertEqual(
        self._module._max_download_workers, expected_max_download_workers
    )
    if output_directory:
      self.assertEqual(self._module._output_directory, output_directory)

  def testProcessWithFolderId(self):
    """Tests the Process method with folder id."""
    # pylint: disable=protected-access
    self._module.SetUp(
        folder_id="folder_id",
        recursive=False,
        drive_ids="",
        max_download_workers=5,
        output_directory=None,
    )

    self.mock_drive_service.files.return_value.list.return_value.execute.return_value = {  # pylint: disable=line-too-long
        "files": [
            {"id": "id1", "name": "file1.txt", "mimeType": "text/plain"},
            {"id": "id2", "name": "file2.txt", "mimeType": "text/plain"},
        ],
        "nextPageToken": None,
    }

    self._module.Process()

    self.mock_drive_service.files.return_value.list.assert_called_with(
        q="'folder_id' in parents and trashed = false",
        spaces="drive",
        fields="nextPageToken, files",
        pageToken=None,
    )
    self.assertEqual(self.mock_media_io.call_count, 2)
    file_containers = self._module.state.GetContainers(
        self._module.name, containers.File
    )
    self.assertLen(file_containers, 2)
    self.assertEqual(file_containers[0].name, "id1")
    self.assertEqual(file_containers[1].name, "id2")
    self.assertEndsWith(file_containers[0].path, "id1_file1.txt")
    self.assertEndsWith(file_containers[1].path, "id2_file2.txt")

  def testProcessWithDriveIds(self):
    """Tests the Process method with drive ids."""
    # pylint: disable=protected-access
    self._module.SetUp(
        folder_id="",
        recursive=False,
        drive_ids="id3,id4",
        max_download_workers=5,
        output_directory=None,
    )

    # Mock drive_resource.files().get().execute() calls
    self.mock_drive_service.files.return_value.get.return_value.execute.side_effect = [  # pylint: disable=line-too-long
        {"id": "id3", "name": "file3.txt", "mimeType": "text/plain"},
        {"id": "id4", "name": "file4.txt", "mimeType": "text/plain"},
    ]

    self._module.Process()

    self.assertEqual(self.mock_media_io.call_count, 2)
    file_containers = self._module.state.GetContainers(
        self._module.name, containers.File
    )
    self.assertEqual(file_containers[0].name, "id3")
    self.assertEqual(file_containers[1].name, "id4")
    self.assertEndsWith(file_containers[0].path, "id3_file3.txt")
    self.assertEndsWith(file_containers[1].path, "id4_file4.txt")

  def testListDriveFolder(self):
    """Tests the ListDriveFolder function."""
    mock_drive_resource = mock.Mock()
    mock_list = mock_drive_resource.files.return_value.list.return_value

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

    self.assertLen(files, 3)
    self.assertSameElements(
        [f["id"] for f in files], ["folder1", "file3", "file4"]
    )


if __name__ == "__main__":
  unittest.main()
