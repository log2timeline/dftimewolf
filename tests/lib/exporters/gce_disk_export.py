#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GoogleCloudDiskExport."""

from __future__ import unicode_literals

import unittest
import os
import mock
from libcloudforensics import gcp

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.exporters import gce_disk_export


FAKE_SOURCE_PROJECT = gcp.GoogleCloudProject(
    'fake-source-project', 'fake-zone')
FAKE_DISK = gcp.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT,
    'fake_zone',
    'fake-source-disk')
FAKE_IMAGE = gcp.GoogleComputeImage(
    FAKE_SOURCE_PROJECT,
    None,
    'fake-source-disk-image-df-export-temp')


class GoogleCloudDiskExportTest(unittest.TestCase):
  """Tests for the Google Cloud disk exporter."""

  def testInitialization(self):
    """Tests that the disk exporter can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    google_disk_export = gce_disk_export.GoogleCloudDiskExport(
        test_state)
    self.assertIsNotNone(google_disk_export)

  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GetDisk')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject')
  def testSetUp(self, mock_gcp_project, mock_get_disk):
    """Tests that the exporter can be initialized."""

    test_state = state.DFTimewolfState(config.Config)
    cloud_disk_exporter = gce_disk_export.GoogleCloudDiskExport(
        test_state)
    mock_gcp_project.return_value = FAKE_SOURCE_PROJECT
    FAKE_SOURCE_PROJECT.GetDisk = mock_get_disk
    mock_get_disk.return_value = FAKE_DISK
    cloud_disk_exporter.SetUp(
        'fake-source-project',
        'fake-source-disk',
        'gs://fake-bucket',
        None,
        None
    )
    self.assertEqual(test_state.errors, [])
    self.assertEqual(cloud_disk_exporter.analysis_project.project_id,
                     'fake-source-project')
    self.assertEqual(cloud_disk_exporter.source_project.project_id,
                     'fake-source-project')
    self.assertEqual(cloud_disk_exporter.source_disk.name,
                     'fake-source-disk')
    self.assertEqual(cloud_disk_exporter.gcs_output_location,
                     'gs://fake-bucket')
    self.assertEqual(cloud_disk_exporter.exported_disk_name,
                     '{0:s}-image-df-export-temp'.format(
                         'fake-source-disk'))

  @mock.patch('libcloudforensics.gcp.GoogleComputeImage.Delete')
  @mock.patch('libcloudforensics.gcp.GoogleComputeImage.ExportImage')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.CreateImageFromDisk')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GetDisk')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject')
  def testProcess(self,
                  mock_gcp_project,
                  mock_get_disk,
                  mock_create_image_from_disk,
                  mock_export_image,
                  mock_delete_image):
    """Tests the exporter's Process() function."""

    test_state = state.DFTimewolfState(config.Config)
    cloud_disk_exporter = gce_disk_export.GoogleCloudDiskExport(
        test_state)
    mock_gcp_project.return_value = FAKE_SOURCE_PROJECT
    FAKE_SOURCE_PROJECT.GetDisk = mock_get_disk
    mock_get_disk.return_value = FAKE_DISK
    cloud_disk_exporter.SetUp(
        'fake-source-project',
        'fake-source-disk',
        'gs://fake-bucket',
        None,
        None
    )
    FAKE_SOURCE_PROJECT.CreateImageFromDisk = mock_create_image_from_disk
    mock_create_image_from_disk.return_value = FAKE_IMAGE
    FAKE_IMAGE.ExportImage = mock_export_image
    FAKE_IMAGE.Delete = mock_delete_image
    cloud_disk_exporter.Process()
    mock_create_image_from_disk.assert_called_with(
        FAKE_DISK, name='{0:s}-image-df-export-temp'.format(
            'fake-source-disk'))
    mock_export_image.assert_called_with(
        'gs://fake-bucket', output_name='{0:s}-image-df-export-temp'.format(
            'fake-source-disk'))
    mock_delete_image.assert_called_once()
    output_uri = os.path.join(
        'gs://fake-bucket', '{0:s}-image-df-export-temp.tar.gz'.format(
            'fake-source-disk'))
    self.assertEqual(test_state.output[0], output_uri)


if __name__ == '__main__':
  unittest.main()
