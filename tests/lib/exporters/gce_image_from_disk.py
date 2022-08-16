#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GCEImageFromDisk module."""

import unittest

from libcloudforensics.providers.gcp.internal import compute
from libcloudforensics.providers.gcp.internal import project as gcp_project
from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.exporters import gce_image_from_disk
import mock


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


class GCEImageFromDiskTest(unittest.TestCase):
  """Tests for the Google Cloud image from disk creator."""

  def testInitialization(self):
    """Tests that the exporter can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    exporter = gce_image_from_disk.GCEImageFromDisk(test_state)
    self.assertIsNotNone(exporter)

  def testSetUp(self):
    """Tests SetUp of the exporter."""
    test_state = state.DFTimewolfState(config.Config)

    exporter = gce_image_from_disk.GCEImageFromDisk(test_state)
    exporter.SetUp('disk-1,disk-2,disk-3',
                   'source-project',
                   'source-zone',
                   'destination-project',
                   'destination-zone',
                   'fake-prefix')

    self.assertEqual('source-project', exporter.source_project)
    self.assertEqual('source-zone', exporter.source_zone)
    self.assertEqual('destination-project', exporter.dest_project)
    self.assertEqual('destination-zone', exporter.dest_zone)
    self.assertEqual('fake-prefix', exporter.name_prefix)

    actual_names = [
        c.name for c in test_state.GetContainers(containers.GCEDisk)]
    expected_names = ['disk-1', 'disk-2', 'disk-3']
    self.assertEqual(sorted(actual_names), sorted(expected_names))

    for project in [
        c.project for c in test_state.GetContainers(containers.GCEDisk)
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

    test_state = state.DFTimewolfState(config.Config)

    exporter = gce_image_from_disk.GCEImageFromDisk(test_state)
    exporter.SetUp(FAKE_DISKS,
                   FAKE_GCP_SOURCE_PROJECT_NAME,
                   FAKE_SOURCE_ZONE,
                   FAKE_GCP_DEST_PROJECT_NAME,
                   FAKE_DEST_ZONE,
                   FAKE_NAME_PREFIX)

    exporter.PreProcess()
    for c in test_state.GetContainers(exporter.GetThreadOnContainerType()):
      exporter.Process(c)  # pytype: disable=wrong-arg-types
      # GetContainers returns the abstract base class type, but process is
      # called with the instantiated child class.
    exporter.PostProcess()

    actual_output = [
        c.name for c in test_state.GetContainers(containers.GCEImage)]

    self.assertEqual(
        sorted(actual_output), sorted(['fake-image-one', 'fake-image-two']))

    for project in [
        c.project for c in test_state.GetContainers(containers.GCEImage)
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

    test_state = state.DFTimewolfState(config.Config)
    for c in FAKE_STATE_OBJECT_LIST:
      test_state.StoreContainer(c)

    exporter = gce_image_from_disk.GCEImageFromDisk(test_state)
    exporter.SetUp(None,
                   FAKE_GCP_SOURCE_PROJECT_NAME,
                   FAKE_SOURCE_ZONE,
                   FAKE_GCP_DEST_PROJECT_NAME,
                   FAKE_DEST_ZONE,
                   FAKE_NAME_PREFIX)

    exporter.PreProcess()
    for c in test_state.GetContainers(exporter.GetThreadOnContainerType()):
      exporter.Process(c)  # pytype: disable=wrong-arg-types
      # GetContainers returns the abstract base class type, but process is
      # called with the instantiated child class.
    exporter.PostProcess()

    actual_output = [c.name for \
        c in test_state.GetContainers(containers.GCEImage)]

    self.assertEqual(sorted(actual_output), sorted([
      'fake-image-one',
      'fake-image-two']))

    for project in [c.project for \
        c in test_state.GetContainers(containers.GCEImage)]:
      self.assertEqual(project, FAKE_GCP_DEST_PROJECT_NAME)


if __name__ == '__main__':
  unittest.main()
