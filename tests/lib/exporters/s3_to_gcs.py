#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the S3ToGCSCopy module."""

import unittest

import mock
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers, aws_containers
from dftimewolf.lib.exporters import s3_to_gcs

FAKE_AWS_REGION = 'fake-region-1'
FAKE_AWS_AZ = FAKE_AWS_REGION + 'a'
FAKE_S3_OBJECTS = 's3://fake-s3-bucket/one,s3://fake-s3-bucket/two'

FAKE_GCP_PROJECT_NAME = 'fake-project'
FAKE_GCS_BUCKET = 'fake-gcs-bucket'
FAKE_GCP_ZONE = 'fake-zone'
FAKE_GCP_PROJECT = gcp_project.GoogleCloudProject(
    FAKE_GCP_PROJECT_NAME)
FAKE_GCP_LIST_BUCKETS_RESPONSE = []
FAKE_GCP_CREATE_BUCKET_RESPONSE = {}

FAKE_STATE_S3_IMAGE_LIST = [
  aws_containers.S3Image('s3://fake-s3-bucket/one', []),
  aws_containers.S3Image('s3://fake-s3-bucket/two', []),
]

FAKE_EXPECTED_OUTPUT = [
  'gs://fake-gcs-bucket/one',
  'gs://fake-gcs-bucket/two'
]

class S3ToGCSCopyTest(unittest.TestCase):
  """Tests for the Google Cloud disk exporter."""

  def testInitialization(self):
    """Tests that the exporter can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    exporter = s3_to_gcs.S3ToGCSCopy(test_state)
    self.assertIsNotNone(exporter)

  def testSetUp(self):
    """Tests SetUp of the exporter."""
    test_state = state.DFTimewolfState(config.Config)

    exporter = s3_to_gcs.S3ToGCSCopy(test_state)
    exporter.SetUp(FAKE_AWS_REGION,
        FAKE_GCP_PROJECT_NAME,
        FAKE_GCS_BUCKET,
        FAKE_S3_OBJECTS)

    self.assertEqual(FAKE_AWS_REGION, exporter.aws_region)
    self.assertEqual(FAKE_GCP_PROJECT_NAME, exporter.dest_project_name)
    self.assertEqual(FAKE_GCS_BUCKET, exporter.dest_bucket)
    self.assertEqual(FAKE_S3_OBJECTS, exporter.s3_objects)

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  @mock.patch('libcloudforensics.providers.gcp.internal.storage.GoogleCloudStorage.ListBuckets')
  @mock.patch('libcloudforensics.providers.gcp.internal.storage.GoogleCloudStorage.CreateBucket')
  @mock.patch('dftimewolf.lib.exporters.s3_to_gcs.S3ToGCSCopy._SetBucketServiceAccountPermissions')
  @mock.patch('libcloudforensics.providers.gcp.internal.storagetransfer.GoogleCloudStorageTransfer.S3ToGCS')
  @mock.patch('time.sleep', return_value=None)
  # pylint: enable=line-too-long
  def testProcessFromParams(self,
      mock_sleep,
      mock_s3_to_gcs,
      mock_set_bucket_perms,
      mock_gcp_create_bucket,
      mock_gcp_list_buckets,
      mock_gcp_project):
    """Tests the exporter's Process() function when the list comes from
    passed in parameters."""
    mock_gcp_project.return_value = FAKE_GCP_PROJECT
    mock_gcp_list_buckets.return_value = FAKE_GCP_LIST_BUCKETS_RESPONSE
    mock_gcp_create_bucket.return_value = FAKE_GCP_CREATE_BUCKET_RESPONSE
    mock_set_bucket_perms.return_value = None
    mock_s3_to_gcs.return_value = None

    test_state = state.DFTimewolfState(config.Config)

    exporter = s3_to_gcs.S3ToGCSCopy(test_state)
    exporter.SetUp(FAKE_AWS_REGION,
        FAKE_GCP_PROJECT_NAME,
        FAKE_GCS_BUCKET,
        FAKE_S3_OBJECTS)

    exporter.Process()

    for output in FAKE_EXPECTED_OUTPUT:
      self.assertIn(output, exporter.state.GetContainers(
          containers.GCSObjectList)[0].object_list)

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.project.GoogleCloudProject')
  @mock.patch('libcloudforensics.providers.gcp.internal.storage.GoogleCloudStorage.ListBuckets')
  @mock.patch('libcloudforensics.providers.gcp.internal.storage.GoogleCloudStorage.CreateBucket')
  @mock.patch('dftimewolf.lib.exporters.s3_to_gcs.S3ToGCSCopy._SetBucketServiceAccountPermissions')
  @mock.patch('libcloudforensics.providers.gcp.internal.storagetransfer.GoogleCloudStorageTransfer.S3ToGCS')
  @mock.patch('time.sleep', return_value=None)
  # pylint: enable=line-too-long
  def testProcessFromState(self,
      mock_sleep,
      mock_s3_to_gcs,
      mock_set_bucket_perms,
      mock_gcp_create_bucket,
      mock_gcp_list_buckets,
      mock_gcp_project):
    """Tests the exporter's Process() function when the list comes from
    a passed in state container."""
    mock_gcp_project.return_value = FAKE_GCP_PROJECT
    mock_gcp_list_buckets.return_value = FAKE_GCP_LIST_BUCKETS_RESPONSE
    mock_gcp_create_bucket.return_value = FAKE_GCP_CREATE_BUCKET_RESPONSE
    mock_set_bucket_perms.return_value = None
    mock_s3_to_gcs.return_value = None

    container = aws_containers.AWSAttributeContainer()
    for s3image in FAKE_STATE_S3_IMAGE_LIST:
      container.AppendS3Image(s3image)
    test_state = state.DFTimewolfState(config.Config)
    test_state.StoreContainer(container)

    exporter = s3_to_gcs.S3ToGCSCopy(test_state)
    exporter.SetUp(FAKE_AWS_REGION,
        FAKE_GCP_PROJECT_NAME,
        FAKE_GCS_BUCKET)

    exporter.Process()

    for output in FAKE_EXPECTED_OUTPUT:
      self.assertIn(output, exporter.state.GetContainers(
          containers.GCSObjectList)[0].object_list)


if __name__ == '__main__':
  unittest.main()
