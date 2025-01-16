#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GCEDiskFromImage module."""

# pytype: disable=attribute-error


import unittest

from libcloudforensics.providers.gcp.internal import compute
from libcloudforensics.providers.gcp.internal import project as gcp_project
import mock
from dftimewolf.lib.containers import containers
from dftimewolf.lib.exporters import gce_disk_from_image
from tests.lib import modules_test_base


FAKE_IMAGES = 'fake-image-one,fake-image-two'
FAKE_GCP_PROJECT_NAME = 'fake-project'
FAKE_ZONE = 'fake-zone-1b'
FAKE_GCP_PROJECT = gcp_project.GoogleCloudProject(
    FAKE_GCP_PROJECT_NAME)
FAKE_DISK_CREATION_RESPONSES = [
    compute.GoogleComputeDisk(FAKE_GCP_PROJECT.project_id, FAKE_ZONE,
                              'fake-disk-one'),
    compute.GoogleComputeDisk(FAKE_GCP_PROJECT.project_id, FAKE_ZONE,
                              'fake-disk-two')
]
FAKE_STATE_GCS_OBJECT_LIST = [
    containers.GCEImage('fake-disk-one', FAKE_GCP_PROJECT_NAME),
    containers.GCEImage('fake-disk-two', FAKE_GCP_PROJECT_NAME)
]


class GCEDiskFromImageTest(modules_test_base.ModuleTestBase):
  """Tests for the Google Cloud disk creator."""

  def setUp(self):
    self._InitModule(gce_disk_from_image.GCEDiskFromImage)
    super().setUp()

  def testSetUp(self):
    """Tests SetUp of the exporter."""
    self._module.SetUp(FAKE_GCP_PROJECT_NAME, FAKE_ZONE, FAKE_IMAGES)

    actual_objects = [c.name for \
        c in self._module.GetContainers(containers.GCEImage)]

    self.assertEqual(FAKE_GCP_PROJECT_NAME, self._module.dest_project_name)
    self.assertEqual(FAKE_ZONE, self._module.dest_zone)
    self.assertEqual(sorted(actual_objects), sorted([
        'fake-image-one',
        'fake-image-two']))

  # pylint: disable=line-too-long,unused-argument
  @mock.patch('googleapiclient.discovery.Resource', return_value = FAKE_GCP_PROJECT)
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.CreateDiskFromImage')
  # pylint: enable=line-too-long
  def testProcessFromParams(self,
      mock_lcf_create_disk_from_image,
      mock_gcp_project):
    """Tests the exporter's Process() function when the list comes from
    passed in parameters."""
    mock_lcf_create_disk_from_image.side_effect = FAKE_DISK_CREATION_RESPONSES

    self._module.SetUp(FAKE_GCP_PROJECT_NAME, FAKE_ZONE, FAKE_IMAGES)

    self._ProcessModule()

    actual_output = [c.name for \
        c in self._module.GetContainers(containers.GCEDisk)]

    self.assertEqual(sorted(actual_output), sorted([
      'fake-disk-one',
      'fake-disk-two']))

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject', return_value = FAKE_GCP_PROJECT)
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.CreateDiskFromImage')
  # pylint: enable=line-too-long
  def testProcessFromState(self,
      mock_lcf_create_disk_from_image,
      mock_gcp_project):
    """Tests the exporter's Process() function when the list comes from
    a passed in state container."""
    mock_lcf_create_disk_from_image.side_effect = FAKE_DISK_CREATION_RESPONSES

    for c in FAKE_STATE_GCS_OBJECT_LIST:
      self._module.StoreContainer(c)

    self._module.SetUp(FAKE_GCP_PROJECT_NAME, FAKE_ZONE)

    self._ProcessModule()

    actual_output = [c.name for \
        c in self._module.GetContainers(containers.GCEDisk)]

    self.assertEqual(sorted(actual_output), sorted([
      'fake-disk-one',
      'fake-disk-two']))


if __name__ == '__main__':
  unittest.main()
