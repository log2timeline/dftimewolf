#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the S3ToGCSCopy module."""

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
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  def testSetUp(
      self,
      mock_gcp_project):
    """Tests that the exporter can be initialized."""

  def testProcessFromParams(self):
    """Tests the exporter's Process() function when the list comes from
    passed in parameters."""

  def testProcessFromState(self):
    """Tests the exporter's Process() function when the list comes from
    a passed in state container."""



if __name__ == '__main__':
  unittest.main()
