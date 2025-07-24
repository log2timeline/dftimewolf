#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GoogleCloudDiskExport."""

import os
import unittest

import mock
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute

from dftimewolf.lib.containers import containers
from dftimewolf.lib.exporters import gce_disk_export
from tests.lib import modules_test_base


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


class GoogleCloudDiskExportTest(modules_test_base.ModuleTestBase):
  """Tests for the Google Cloud disk exporter."""

  # For pytype
  _module: gce_disk_export.GoogleCloudDiskExport

  def setUp(self):
    self._InitModule(gce_disk_export.GoogleCloudDiskExport)
    super().setUp()

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  def testSetUp(
      self,
      mock_gcp_project,
      mock_get_disk):
    """Tests that the exporter can be initialized."""
    mock_gcp_project.return_value = FAKE_SOURCE_PROJECT
    FAKE_SOURCE_PROJECT.compute.GetDisk = mock_get_disk
    mock_get_disk.return_value = FAKE_DISK
    self._module.SetUp(
        'fake-source-project',
        'gs://fake-bucket',
        None,
        'fake-source-disk',
        None,
        False,
        'image-df-export-temp'
    )
    self.assertEqual(self._module.analysis_project.project_id,
                     'fake-source-project')
    self.assertEqual(self._module.source_project.project_id,
                     'fake-source-project')
    self.assertEqual(self._module.source_disks[0].name,
                     'fake-source-disk')
    self.assertEqual(self._module.gcs_output_location,
                     'gs://fake-bucket')
    self.assertEqual(self._module.exported_image_name,
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
    mock_export_image.return_value = 'gs://fake-bucket/image-df-export-temp.tar.gz'
    mock_gcp_project.return_value = FAKE_SOURCE_PROJECT
    FAKE_SOURCE_PROJECT.compute.GetDisk = mock_get_disk
    mock_get_disk.return_value = FAKE_DISK
    self._module.SetUp(
        source_project_name='fake-source-project',
        gcs_output_location='gs://fake-bucket',
        source_disk_names='fake-source-disk',
        exported_image_name='image-df-export-temp',
        image_format='qcow2'
    )
    FAKE_SOURCE_PROJECT.compute.CreateImageFromDisk = mock_create_image_from_disk
    mock_create_image_from_disk.return_value = FAKE_IMAGE
    FAKE_IMAGE.ExportImage = mock_export_image
    FAKE_IMAGE.Delete = mock_delete_image
    self._ProcessModule()
    mock_create_image_from_disk.assert_called_with(
        FAKE_DISK)
    mock_export_image.assert_called_with(
        'gs://fake-bucket',
        output_name='image-df-export-temp',
        image_format='qcow2')
    mock_delete_image.assert_called_once()
    output_url = os.path.join(
        'gs://fake-bucket', 'image-df-export-temp.tar.gz')
    urls = self._module.GetContainers(containers.GCSObject)
    self.assertEqual(urls[0].path, output_url)


if __name__ == '__main__':
  unittest.main()
