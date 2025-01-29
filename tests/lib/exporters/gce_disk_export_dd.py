#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GoogleCloudDiskExportStream."""

import unittest

import mock
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute

from dftimewolf.lib.exporters import gce_disk_export_dd
from tests.lib import modules_test_base


FAKE_SOURCE_PROJECT = gcp_project.GoogleCloudProject(
    'fake-source-project', 'fake-zone')
FAKE_DISK = compute.GoogleComputeDisk(
    FAKE_SOURCE_PROJECT.project_id,
    'fake_zone',
    'fake-source-disk')
FAKE_INSTANCE = compute.GoogleComputeInstance(
    FAKE_SOURCE_PROJECT.project_id,
    'fake_zone',
    'fake-instance')


class GoogleCloudDiskExportStreamTest(modules_test_base.ModuleTestBase):
  """Tests for the Google Cloud disk bit-stream export."""

  def setUp(self):
    self._InitModule(gce_disk_export_dd.GoogleCloudDiskExportStream)
    super().setUp()

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeDisk.GetOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  def testSetUp(
      self,
      mock_gcp_project,
      mock_get_disk,
      mock_disk_get_operation):
    """Tests that the exporter can be initialized."""
    mock_gcp_project.return_value = FAKE_SOURCE_PROJECT
    FAKE_SOURCE_PROJECT.compute.GetDisk = mock_get_disk
    mock_get_disk.return_value = FAKE_DISK
    mock_disk_get_operation.return_value = {}
    self._module.SetUp(
        'fake-source-project',
        'gs://fake-bucket',
        'fake-source-disk',
        None,
        False
    )
    self.assertEqual(self._module.source_project.project_id,
                     'fake-source-project')
    self.assertEqual(self._module.source_disks[0].name,
                     'fake-source-disk')
    self.assertEqual(self._module.gcs_output_location,
                     'gs://fake-bucket/')

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeDisk.GetLabels')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.Delete')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeDisk.GetOperation')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.CreateInstanceFromArguments')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  def testProcess(self,
                  mock_gcp_project,
                  mock_get_disk,
                  mock_create_instance_from_arguments,
                  mock_disk_get_operation,
                  mock_delete_instance,
                  mock_get_disk_labels,
                  mock_instance_get_operation):
    """Tests the exporter's Process() function."""
    mock_gcp_project.return_value = FAKE_SOURCE_PROJECT
    FAKE_SOURCE_PROJECT.compute.GetDisk = mock_get_disk
    mock_get_disk.return_value = FAKE_DISK
    mock_disk_get_operation.return_value = {}
    self._module.SetUp(
        'fake-source-project',
        'gs://fake-bucket',
        'fake-source-disk',
        None,
        False
    )
    FAKE_SOURCE_PROJECT.compute.CreateInstanceFromArgument = mock_create_instance_from_arguments
    mock_create_instance_from_arguments.return_value = FAKE_INSTANCE
    mock_get_disk_labels.return_value = {'archive_hash_verified': 'true'}
    mock_instance_get_operation.return_value = {}
    self._ProcessModule()
    mock_delete_instance.assert_called_once()
    mock_create_instance_from_arguments.assert_called_once()


if __name__ == '__main__':
  unittest.main()
