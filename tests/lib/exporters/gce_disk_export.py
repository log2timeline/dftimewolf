#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GoogleCloudDiskExport."""

import os
import unittest

from googleapiclient.errors import HttpError
import httplib2
import mock
from libcloudforensics import errors as lcf_errors
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


# pylint: disable=line-too-long


class GoogleCloudDiskExportTest(modules_test_base.ModuleTestBase):
  """Tests for the Google Cloud disk exporter."""

  _module: gce_disk_export.GoogleCloudDiskExport  # pyrefly: ignore[bad-override-mutable-attribute]

  def setUp(self):
    self._InitModule(gce_disk_export.GoogleCloudDiskExport)
    super().setUp()

  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage.Delete')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage.ExportImage')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.CreateImageFromDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  def testProcessDiskParams(self,
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
    self._module.SetUp(source_project_name='fake-source-project',
                       gcs_output_location='gs://fake-bucket',
                       analysis_project_name='',
                       source_disk_names='fake-source-disk',
                       remote_instance_name='',
                       all_disks=False,
                       exported_image_name='image-df-export-temp',
                       image_format='qcow2',
                       cloudbuild_zone='zone1')
    FAKE_SOURCE_PROJECT.compute.CreateImageFromDisk = mock_create_image_from_disk
    mock_create_image_from_disk.return_value = FAKE_IMAGE
    FAKE_IMAGE.ExportImage = mock_export_image
    FAKE_IMAGE.Delete = mock_delete_image
    self._ProcessModule()
    mock_create_image_from_disk.assert_called_with(
        FAKE_DISK, name=mock.ANY)
    mock_export_image.assert_called_with(
        'gs://fake-bucket',
        output_name='image-df-export-temp',
        image_format='qcow2',
        zone='zone1')
    mock_delete_image.assert_called_once()
    output_url = os.path.join(
        'gs://fake-bucket', 'image-df-export-temp.tar.gz')
    urls = self._module.GetContainers(containers.GCSObject)
    self.assertLen(urls, 1)
    self.assertEqual(urls[0].path, output_url)
    self.assertIn('SOURCE_DISK', urls[0].metadata)
    self.assertIn('SOURCE_MACHINE', urls[0].metadata)
    self.assertEqual(urls[0].metadata['SOURCE_DISK'], 'fake-source-disk')
    self.assertEqual(urls[0].metadata['SOURCE_MACHINE'], 'UNKNOWN_MACHINE')

  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage.Delete')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage.ExportImage')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.CreateImageFromDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  def testProcessDiskFromState(self,
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
    self._module.SetUp(source_project_name='fake-source-project',
                       gcs_output_location='gs://fake-bucket',
                       analysis_project_name='',
                       source_disk_names='',
                       remote_instance_name='',
                       all_disks=False,
                       exported_image_name='image-df-export-temp',
                       image_format='qcow2',
                       cloudbuild_zone='zone1')

    container = containers.GCEDisk(name='fake-source-disk', project='fake-source-project')
    container.metadata['SOURCE_MACHINE'] = 'fake-source-machine'
    container.metadata['SOURCE_DISK'] = 'fake-source-disk'
    self._module.StoreContainer(container)

    FAKE_SOURCE_PROJECT.compute.CreateImageFromDisk = mock_create_image_from_disk
    mock_create_image_from_disk.return_value = FAKE_IMAGE
    FAKE_IMAGE.ExportImage = mock_export_image
    FAKE_IMAGE.Delete = mock_delete_image
    self._ProcessModule()
    mock_create_image_from_disk.assert_called_with(
        FAKE_DISK, name=mock.ANY)
    mock_export_image.assert_called_with(
        'gs://fake-bucket',
        output_name='image-df-export-temp',
        image_format='qcow2',
        zone='zone1')
    mock_delete_image.assert_called_once()
    output_url = os.path.join(
        'gs://fake-bucket', 'image-df-export-temp.tar.gz')
    urls = self._module.GetContainers(containers.GCSObject)
    self.assertLen(urls, 1)
    self.assertEqual(urls[0].path, output_url)
    self.assertIn('SOURCE_DISK', urls[0].metadata)
    self.assertIn('SOURCE_MACHINE', urls[0].metadata)
    self.assertEqual(urls[0].metadata['SOURCE_DISK'], 'fake-source-disk')
    self.assertEqual(urls[0].metadata['SOURCE_MACHINE'], 'fake-source-machine')

  def _SetUpResumeTest(self,
                       mock_get_disk: mock.MagicMock,
                       mock_create_image_from_disk: mock.MagicMock) -> None:
    """Sets up the module with the arguments of the resume tests."""
    self._module.SetUp(source_project_name='fake-source-project',
                       gcs_output_location='gs://fake-bucket',
                       analysis_project_name='',
                       source_disk_names='fake-source-disk',
                       remote_instance_name='',
                       all_disks=False,
                       exported_image_name='',
                       image_format='',
                       cloudbuild_zone='zone1')
    FAKE_SOURCE_PROJECT.compute.GetDisk = mock_get_disk
    FAKE_SOURCE_PROJECT.compute.CreateImageFromDisk = mock_create_image_from_disk

  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage.Delete')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage.ExportImage')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.CreateImageFromDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  def testResumeExportsAgainFromTheSameImage(self,
                                             mock_gcp_project,
                                             mock_get_disk,
                                             mock_create_image_from_disk,
                                             mock_export_image,
                                             mock_delete_image):
    """Tests a resumed run after a crash during the export.

    The resumed run uses the image name of the earlier run, so it finds the
    image of that run, and exports again from it.
    """
    mock_gcp_project.return_value = FAKE_SOURCE_PROJECT
    mock_get_disk.return_value = FAKE_DISK
    mock_create_image_from_disk.side_effect = [
        FAKE_IMAGE,
        lcf_errors.ResourceAlreadyExistsError('Image exists', __name__),
    ]
    mock_export_image.side_effect = [
        RuntimeError('Crash'), 'gs://fake-bucket/fake-image.tar.gz']
    self._KeepResumeKeys()
    self._SetUpResumeTest(mock_get_disk, mock_create_image_from_disk)
    with self.assertRaisesRegex(RuntimeError, 'Crash'):
      self._ProcessModule()

    self._ResumeModule()
    self._SetUpResumeTest(mock_get_disk, mock_create_image_from_disk)
    self._ProcessModule()

    first_call, second_call = mock_create_image_from_disk.call_args_list
    self.assertEqual(second_call, first_call)
    self.assertEqual(mock_export_image.call_count, 2)
    mock_delete_image.assert_called_once()
    urls = self._module.GetContainers(containers.GCSObject)
    self.assertEqual([u.path for u in urls],
                     ['gs://fake-bucket/fake-image.tar.gz'])

  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage.Delete')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeImage.ExportImage')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.CreateImageFromDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  def testResumeReusesTheExport(self,
                                mock_gcp_project,
                                mock_get_disk,
                                mock_create_image_from_disk,
                                mock_export_image,
                                mock_delete_image):
    """Tests a resumed run after a crash between the export and the delete.

    The resumed run reuses the export, and deletes the image. It ignores an
    image that is gone already.
    """
    mock_gcp_project.return_value = FAKE_SOURCE_PROJECT
    mock_get_disk.return_value = FAKE_DISK
    mock_create_image_from_disk.return_value = FAKE_IMAGE
    mock_export_image.return_value = 'gs://fake-bucket/fake-image.tar.gz'
    mock_delete_image.side_effect = [
        RuntimeError('Crash'),
        HttpError(httplib2.Response({'status': 404}), b'Not found'),
    ]
    self._KeepResumeKeys()
    self._SetUpResumeTest(mock_get_disk, mock_create_image_from_disk)
    with self.assertRaisesRegex(RuntimeError, 'Crash'):
      self._ProcessModule()

    self._ResumeModule()
    self._SetUpResumeTest(mock_get_disk, mock_create_image_from_disk)
    self._ProcessModule()

    mock_create_image_from_disk.assert_called_once()
    mock_export_image.assert_called_once()
    self.assertEqual(mock_delete_image.call_count, 2)
    urls = self._module.GetContainers(containers.GCSObject)
    self.assertEqual([u.path for u in urls],
                     ['gs://fake-bucket/fake-image.tar.gz'])

if __name__ == '__main__':
  unittest.main()
