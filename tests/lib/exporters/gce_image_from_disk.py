#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GCEImageFromDisk module."""

# pytype: disable=attribute-error

import unittest

from libcloudforensics.providers.gcp.internal import compute
from libcloudforensics.providers.gcp.internal import project as gcp_project
import mock
from dftimewolf.lib.containers import containers
from dftimewolf.lib.exporters import gce_image_from_disk
from tests.lib import modules_test_base


FAKE_DISKS = 'fake-disk-one,fake-disk-two'
FAKE_GCP_SOURCE_PROJECT_NAME = 'fake-source-project'
FAKE_SOURCE_ZONE = 'fake-zone-source'
FAKE_GCP_DEST_PROJECT_NAME = 'fake-source-dest'
FAKE_DEST_ZONE = 'fake-zone-dest'
FAKE_NAME_PREFIX = 'fake-name-prefix'
FAKE_GCP_SOURCE_PROJECT = gcp_project.GoogleCloudProject(
    FAKE_GCP_SOURCE_PROJECT_NAME)
FAKE_GCP_DEST_PROJECT = gcp_project.GoogleCloudProject(
    FAKE_GCP_DEST_PROJECT_NAME)
FAKE_DISK_CREATION_RESPONSES = [
    compute.GoogleComputeImage(FAKE_GCP_DEST_PROJECT.project_id, FAKE_DEST_ZONE,
                               'fake-image-one'),
    compute.GoogleComputeImage(FAKE_GCP_DEST_PROJECT.project_id, FAKE_DEST_ZONE,
                               'fake-image-two')
]
FAKE_STATE_OBJECT_LIST = [
    containers.GCEDisk('fake-disk-one', FAKE_GCP_SOURCE_PROJECT_NAME),
    containers.GCEDisk('fake-disk-two', FAKE_GCP_SOURCE_PROJECT_NAME)
]


class GCEImageFromDiskTest(modules_test_base.ModuleTestBase):
  """Tests for the Google Cloud image from disk creator."""

  def setUp(self):
    self._InitModule(gce_image_from_disk.GCEImageFromDisk)
    super().setUp()

  def testSetUp(self):
    """Tests SetUp of the exporter."""
    self._module.SetUp('disk-1,disk-2,disk-3',
                   'source-project',
                   'source-zone',
                   'destination-project',
                   'destination-zone',
                   'fake-prefix')

    self.assertEqual('source-project', self._module.source_project)
    self.assertEqual('source-zone', self._module.source_zone)
    self.assertEqual('destination-project', self._module.dest_project)
    self.assertEqual('destination-zone', self._module.dest_zone)
    self.assertEqual('fake-prefix', self._module.name_prefix)

    actual_names = [
        c.name for c in self._module.GetContainers(containers.GCEDisk)]
    expected_names = ['disk-1', 'disk-2', 'disk-3']
    self.assertEqual(sorted(actual_names), sorted(expected_names))

    for project in [
        c.project for c in self._module.GetContainers(containers.GCEDisk)
    ]:
      self.assertEqual(project, 'source-project')

  # pylint: disable=line-too-long,unused-argument
  @mock.patch('googleapiclient.discovery.Resource', return_value=FAKE_GCP_SOURCE_PROJECT)
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.CreateImageFromDisk')
  # pylint: enable=line-too-long
  def testProcessFromParams(self, mock_lcf_create_image_from_disk,
                            mock_gcp_project):
    """Tests the exporter's Process() when the list comes from parameters."""
    mock_lcf_create_image_from_disk.side_effect = FAKE_DISK_CREATION_RESPONSES

    self._module.SetUp(FAKE_DISKS,
                   FAKE_GCP_SOURCE_PROJECT_NAME,
                   FAKE_SOURCE_ZONE,
                   FAKE_GCP_DEST_PROJECT_NAME,
                   FAKE_DEST_ZONE,
                   FAKE_NAME_PREFIX)

    self._ProcessModule()

    actual_output = [
        c.name for c in self._module.GetContainers(containers.GCEImage)]

    self.assertEqual(
        sorted(actual_output), sorted(['fake-image-one', 'fake-image-two']))

    for project in [
        c.project for c in self._module.GetContainers(containers.GCEImage)
    ]:
      self.assertEqual(project, FAKE_GCP_DEST_PROJECT_NAME)

    # Using mock.ANY since we don't have access to the
    # gcp.internal.compute.GoogleComputeDisk from tests.
    mock_lcf_create_image_from_disk.assert_has_calls([
        mock.call(mock.ANY, name=mock.ANY),
        mock.call(mock.ANY, name=mock.ANY),
    ])

  # pylint: disable=line-too-long,unused-argument
  @mock.patch('googleapiclient.discovery.Resource', return_value=FAKE_GCP_SOURCE_PROJECT)
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.CreateImageFromDisk')
  # pylint: enable=line-too-long
  def testProcessFromState(self, mock_lcf_create_image_from_disk,
                           mock_gcp_project):
    """Tests the exporter's Process() function when the list comes from
    passed in parameters."""
    mock_lcf_create_image_from_disk.side_effect = FAKE_DISK_CREATION_RESPONSES

    for c in FAKE_STATE_OBJECT_LIST:
      self._module.StoreContainer(c)

    self._module.SetUp(None,
                   FAKE_GCP_SOURCE_PROJECT_NAME,
                   FAKE_SOURCE_ZONE,
                   FAKE_GCP_DEST_PROJECT_NAME,
                   FAKE_DEST_ZONE,
                   FAKE_NAME_PREFIX)

    self._ProcessModule()

    actual_output = [c.name for \
        c in self._module.GetContainers(containers.GCEImage)]

    self.assertEqual(sorted(actual_output), sorted([
      'fake-image-one',
      'fake-image-two']))

    for project in [c.project for \
        c in self._module.GetContainers(containers.GCEImage)]:
      self.assertEqual(project, FAKE_GCP_DEST_PROJECT_NAME)


if __name__ == '__main__':
  unittest.main()
