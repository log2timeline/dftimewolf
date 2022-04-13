#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GCStoGCEImage module."""

import unittest

import mock
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.exporters import gcs_to_gce_image


FAKE_GCS_OBJECTS = 'gs://fake-gcs-bucket/one,gs://fake-gcs-bucket/two'
FAKE_GCP_PROJECT_NAME = 'fake-project'
FAKE_GCP_PROJECT = gcp_project.GoogleCloudProject(
    FAKE_GCP_PROJECT_NAME)
FAKE_ROLE_LIST = {
  'roles': [
    {
      'name': 'projects/fake-project/roles/disk_build_role',
      'title': 'disk_build_role',
      'description': 'disk_build_role',
      'etag': 'BwXMs700pUk='
    }
  ]
}
FAKE_PROJECT_GET = {
  'projectNumber': '123456789012'
}
FAKE_IMPORT_IMAGE_RESPONSES = [
  compute.GoogleComputeImage(
    FAKE_GCP_PROJECT,
    'fake_zone',
    'fake-gcs-bucket-one'),
  compute.GoogleComputeImage(FAKE_GCP_PROJECT,
  'fake_zone',
  'fake-gcs-bucket-two')
]
FAKE_STATE_GCS_OBJECT_LIST = [
  containers.GCSObject('gs://fake-gcs-bucket/one'),
  containers.GCSObject('gs://fake-gcs-bucket/two')
]


class GCSToGCEImageTest(unittest.TestCase):
  """Tests for the Google Cloud disk exporter."""

  def testInitialization(self):
    """Tests that the exporter can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    exporter = gcs_to_gce_image.GCSToGCEImage(test_state)
    self.assertIsNotNone(exporter)

  # pylint: disable=line-too-long,unused-argument
  @mock.patch('libcloudforensics.providers.gcp.internal.common.default', return_value = ('', None))
  # pylint: enable=line-too-long
  def testSetUp(self, mock_auth_default):
    """Tests SetUp of the exporter."""
    test_state = state.DFTimewolfState(config.Config)

    exporter = gcs_to_gce_image.GCSToGCEImage(test_state)
    exporter.SetUp(FAKE_GCP_PROJECT_NAME, FAKE_GCS_OBJECTS)

    actual_objects = [c.path for \
        c in test_state.GetContainers(containers.GCSObject)]

    self.assertEqual(FAKE_GCP_PROJECT_NAME, exporter.dest_project_name)
    self.assertEqual(sorted(actual_objects), sorted([
        'gs://fake-gcs-bucket/one',
        'gs://fake-gcs-bucket/two']))

  # pylint: disable=line-too-long,unused-argument
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject', return_value = FAKE_GCP_PROJECT)
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ImportImageFromStorage')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.default', return_value = ('', None))
  @mock.patch('googleapiclient.discovery.Resource')
  @mock.patch('time.sleep', return_value=None)
  # pylint: enable=line-too-long
  def testProcessFromParams(self,
      mock_sleep,
      mock_gcp_service,
      mock_auth_default,
      mock_lcf_import_image_from_storage,
      mock_gcp_project):
    """Tests the exporter's Process() function when the list comes from
    passed in parameters."""
    mock_lcf_import_image_from_storage.side_effect = FAKE_IMPORT_IMAGE_RESPONSES
    mock_gcp_service().roles().list().execute.return_value = FAKE_ROLE_LIST
    mock_gcp_service().roles().list_next.return_value = None
    mock_gcp_service().projects().get().execute.return_value = FAKE_PROJECT_GET

    test_state = state.DFTimewolfState(config.Config)

    exporter = gcs_to_gce_image.GCSToGCEImage(test_state)
    exporter.SetUp(FAKE_GCP_PROJECT_NAME, FAKE_GCS_OBJECTS)

    exporter.PreProcess()
    for c in test_state.GetContainers(exporter.GetThreadOnContainerType()):
      exporter.Process(c)  # pytype: disable=wrong-arg-types
      # GetContainers returns the abstract base class type, but process is
      # called with the instantiated child class.
    exporter.PostProcess()

    actual_output = [c.name for \
        c in test_state.GetContainers(containers.GCEImage)]

    self.assertEqual(sorted(actual_output), sorted([
        'fake-gcs-bucket-one',
        'fake-gcs-bucket-two']))

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject', return_value = FAKE_GCP_PROJECT)
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.ImportImageFromStorage')
  @mock.patch('libcloudforensics.providers.gcp.internal.common.default', return_value = ('', None))
  @mock.patch('googleapiclient.discovery.Resource')
  @mock.patch('time.sleep', return_value=None)
  # pylint: enable=line-too-long
  def testProcessFromState(self,
      mock_sleep,
      mock_gcp_service,
      mock_auth_default,
      mock_lcf_import_image_from_storage,
      mock_gcp_project):
    """Tests the exporter's Process() function when the list comes from
    a passed in state container."""
    mock_gcp_service().roles().list().execute.return_value = FAKE_ROLE_LIST
    mock_gcp_service().roles().list_next.return_value = None
    mock_gcp_service().projects().get().execute.return_value = FAKE_PROJECT_GET
    mock_lcf_import_image_from_storage.side_effect = FAKE_IMPORT_IMAGE_RESPONSES

    test_state = state.DFTimewolfState(config.Config)
    for c in FAKE_STATE_GCS_OBJECT_LIST:
      test_state.StoreContainer(c)

    exporter = gcs_to_gce_image.GCSToGCEImage(test_state)
    exporter.SetUp(FAKE_GCP_PROJECT_NAME)

    exporter.PreProcess()
    for c in test_state.GetContainers(exporter.GetThreadOnContainerType()):
      exporter.Process(c)  # pytype: disable=wrong-arg-types
      # GetContainers returns the abstract base class type, but process is
      # called with the instantiated child class.
    exporter.PostProcess()

    actual_output = [c.name for \
        c in test_state.GetContainers(containers.GCEImage)]

    self.assertEqual(sorted(actual_output), sorted([
        'fake-gcs-bucket-one',
        'fake-gcs-bucket-two']))


if __name__ == '__main__':
  unittest.main()
