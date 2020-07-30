#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GoogleCloudDiskExport."""

import os
import unittest

import mock
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.exporters import gce_disk_export


FAKE_SOURCE_PROJECT = gcp_project.GoogleCloudProject(
    'fake-source-project', 'fake-zone')
FAKE_DISK = compute.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT.project_id,
    'fake_zone',
    'fake-source-disk')
FAKE_IMAGE = compute.GoogleComputeImage(
    FAKE_SOURCE_PROJECT.project_id,
    'fake-zone',
    'fake-source-disk-image-df-export-temp')


class GoogleCloudDiskExportTest(unittest.TestCase):
  """Tests for the Google Cloud disk exporter."""

  def testInitialization(self):
    """Tests that the disk exporter can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    google_disk_export = gce_disk_export.GoogleCloudDiskExport(
        test_state)
    self.assertIsNotNone(google_disk_export)

  # pylint: disable=line-too-long
  @mock.patch('dftimewolf.lib.collectors.gcloud.GoogleCloudCollector.FindDisksToCopy')
  @mock.patch('dftimewolf.lib.collectors.gcloud.GoogleCloudCollector.SetUp')
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  def testSetUp(
      self,
      mock_gcp_project,
      mock_gcloud_setup,
      mock_gcloud_find_disk):
    """Tests that the exporter can be initialized."""

    test_state = state.DFTimewolfState(config.Config)
    cloud_disk_exporter = gce_disk_export.GoogleCloudDiskExport(
        test_state)
    mock_gcp_project.return_value = FAKE_SOURCE_PROJECT
    mock_gcloud_setup.side_effect = None
    mock_gcloud_find_disk.return_value = [FAKE_DISK]
    cloud_disk_exporter.SetUp(
        'fake-source-project',
        'gs://fake-bucket',
        None,
        'fake-source-disk',
        None,
        False,
        'image-df-export-temp'
    )
    self.assertEqual(test_state.errors, [])
    self.assertEqual(cloud_disk_exporter.analysis_project.project_id,
                     'fake-source-project')
    self.assertEqual(cloud_disk_exporter.source_project.project_id,
                     'fake-source-project')
    self.assertEqual(cloud_disk_exporter.source_disks[0].name,
                     'fake-source-disk')
    self.assertEqual(cloud_disk_exporter.gcs_output_location,
                     'gs://fake-bucket')
    self.assertEqual(cloud_disk_exporter.exported_image_name,
                     'image-df-export-temp')

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage.Delete')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage.ExportImage')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.CreateImageFromDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
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
    FAKE_SOURCE_PROJECT.compute.GetDisk = mock_get_disk
    mock_get_disk.return_value = FAKE_DISK
    cloud_disk_exporter.SetUp(
        source_project_name='fake-source-project',
        gcs_output_location='gs://fake-bucket',
        disk_names='fake-source-disk',
        exported_image_name='image-df-export-temp'
    )
    FAKE_SOURCE_PROJECT.compute.CreateImageFromDisk = mock_create_image_from_disk
    mock_create_image_from_disk.return_value = FAKE_IMAGE
    FAKE_IMAGE.ExportImage = mock_export_image
    FAKE_IMAGE.Delete = mock_delete_image
    cloud_disk_exporter.Process()
    mock_create_image_from_disk.assert_called_with(
        FAKE_DISK)
    mock_export_image.assert_called_with(
        'gs://fake-bucket', output_name='image-df-export-temp')
    mock_delete_image.assert_called_once()
    output_url = os.path.join(
        'gs://fake-bucket', 'image-df-export-temp.tar.gz')
    urls = test_state.GetContainers(containers.URL)
    self.assertEqual(urls[0].path, output_url)


if __name__ == '__main__':
  unittest.main()
