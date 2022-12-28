#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GoogleCloudCollector."""

import unittest
from typing import Any

import mock
import botocore

from libcloudforensics.providers.aws.internal import account as aws_account
from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.collectors import aws_snapshot_s3_copy


FAKE_BUCKET = 'fake-bucket'
FAKE_SUBNET = 'sub-01234567'
FAKE_REGION = 'fake-region-1'
FAKE_AZ_B = 'fake-region-1b'
FAKE_AZ_A = 'fake-region-1a'
with mock.patch('boto3.session.Session._setup_loader') as mock_session:
  mock_session.return_value = None
  FAKE_AWS_ACCOUNT = aws_account.AWSAccount(
      default_availability_zone=FAKE_AZ_A)

# libcloudforensics mock responses
FAKE_PROFILE_NAME = 'ebsCopy'
FAKE_EBS_COPY_SETUP_RESPONSE = {
  'profile': {
    'arn': 'arn:aws:iam::123456789012:instance-profile/ebsCopy-role',
    'created': True },
  'policy': {
    'arn': 'arn:aws:iam::123456789012:policy/ebsCopy-policy',
    'created': True },
  'role': {
    'name': 'ebsCopy-role',
    'created': True }
}
FAKE_EBS_COPY_PROCESS_RESPONSE = [{
    'image': 's3://fake-bucket/snap-01234567/image.bin',
    'hashes': [
      's3://fake-bucket/snap-01234567/log.txt',
      's3://fake-bucket/snap-01234567/hlog.txt',
      's3://fake-bucket/snap-01234567/mlog.txt'
    ]
  }, {
    'image': 's3://fake-bucket/snap-12345678/image.bin',
    'hashes': [
      's3://fake-bucket/snap-12345678/log.txt',
      's3://fake-bucket/snap-12345678/hlog.txt',
      's3://fake-bucket/snap-12345678/mlog.txt'
    ]
  }
]

# Mirrors the responses from AWS APIs (minus unnecessary fields)
FAKE_SNAPSHOT_1 = {
  'SnapshotId': 'snap-01234567',
  'State': 'completed',
  'VolumeSize': 1
}
FAKE_SNAPSHOT_2 = {
  'SnapshotId': 'snap-12345678',
  'State': 'completed',
  'VolumeSize': 1
}
FAKE_DESCRIBE_SNAPSHOTS = {
  'Snapshots': [FAKE_SNAPSHOT_1, FAKE_SNAPSHOT_2]
}
FAKE_DESCRIBE_AVAILABILITY_ZONES = {
  'AvailabilityZones': [
    {
      'State': 'available',
      'OptInStatus': 'opt-in-not-required',
      'RegionName': FAKE_REGION,
      'ZoneName': FAKE_AZ_A,
      'ZoneId': 'fake-az2',
      'GroupName': FAKE_REGION,
      'NetworkBorderGroup': FAKE_REGION,
      'ZoneType': 'availability-zone',
    },
  ]
}
FAKE_DESCRIBE_SUBNETS = {
  'Subnets': [
    {
      'AvailabilityZone': FAKE_AZ_B,
      'AvailabilityZoneId': 'fake-az2',
      'State': 'available',
      'SubnetId': FAKE_SUBNET
    }
  ]
}
FAKE_LIST_BUCKETS_RESPONSE = {
  'Buckets': [
    {
      'Name': 'bucket-1'
    }
  ]
}
FAKE_CREATE_BUCKET_RESPONSE = None

# pylint: disable=protected-access
orig = botocore.client.BaseClient._make_api_call

def MockMakeAPICall(self, operation_name: str, kwarg: Any) -> Any:
  """Mock the boto3 api calls for specified client methods.

  Args:
    operation_name: The AWS API operation.
    kwarg: Args to pass to the method.

  Returns:
    The result of a mock API call, if available.
  """
  if operation_name == 'DescribeSnapshots':
    return FAKE_DESCRIBE_SNAPSHOTS
  if operation_name == 'DescribeAvailabilityZones':
    return FAKE_DESCRIBE_AVAILABILITY_ZONES
  if operation_name == 'DescribeSubnets':
    return FAKE_DESCRIBE_SUBNETS
  if operation_name == 'ListBuckets':
    return FAKE_LIST_BUCKETS_RESPONSE
  if operation_name == 'CreateBucket':
    return FAKE_CREATE_BUCKET_RESPONSE
  return orig(self, operation_name, kwarg)

class AWSSnapshotS3CopyCollectorTest(unittest.TestCase):
  """Tests for the AWSSnapshotS3CopyCollector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)
    self.assertIsNotNone(collector)

  def testSetUp(self):
    """Tests SetUp of the collector."""
    test_state = state.DFTimewolfState(config.Config)

    # Subnet is optional - test with it.
    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):

      collector.SetUp(','.join([snapshot['SnapshotId']\
            for snapshot in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']]),
          FAKE_BUCKET,
          FAKE_REGION,
          FAKE_SUBNET)

    state_snaps = [snap.id for snap in \
        collector.GetContainers(containers.AWSSnapshot)]

    self.assertEqual(['snap-01234567', 'snap-12345678'], state_snaps)
    self.assertEqual(FAKE_REGION, collector.region)
    self.assertEqual(FAKE_BUCKET, collector.bucket)
    self.assertEqual(FAKE_SUBNET, collector.subnet)

    # Subnet is optional - test without it.
    test_state = state.DFTimewolfState(config.Config)
    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):
      collector.SetUp(','.join([snapshot['SnapshotId']\
            for snapshot in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']]),
          FAKE_BUCKET,
          FAKE_REGION)

    state_snaps = [snap.id for snap in \
        collector.GetContainers(containers.AWSSnapshot)]

    self.assertEqual(['snap-01234567', 'snap-12345678'], state_snaps)
    self.assertEqual(FAKE_REGION, collector.region)
    self.assertEqual(FAKE_BUCKET, collector.bucket)
    self.assertEqual(None, collector.subnet)

  @mock.patch('boto3.session.Session._setup_loader')
  def testPickAvailabilityZone(self, mock_loader):
    """Test the utility function that picks an availability zone in the
    region to use."""
    mock_loader.return_value = None

    test_state = state.DFTimewolfState(config.Config)
    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):

      snaps_str = ','.join(
          [s['SnapshotId'] for s in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']])
      collector.SetUp(snaps_str,
          FAKE_BUCKET,
          FAKE_REGION)

      # Test without a subnet ID
      result = collector._PickAvailabilityZone()
      self.assertEqual(result, FAKE_AZ_A)

      # Test with a subnet ID
      result = collector._PickAvailabilityZone(FAKE_SUBNET)
      self.assertEqual(result, FAKE_AZ_B)

  # pylint: disable=line-too-long
  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.forensics.CopyEBSSnapshotToS3SetUp')
  @mock.patch('libcloudforensics.providers.aws.forensics.CopyEBSSnapshotToS3Process')
  @mock.patch('libcloudforensics.providers.aws.forensics.CopyEBSSnapshotToS3TearDown')
  @mock.patch('time.sleep', return_value=None)
  # pylint: enable=line-too-long
  def testProcessFromParams(self,
      mock_sleep,
      mock_copyebssnapshottos3teardown,
      mock_copyebssnapshottos3process,
      mock_copyebssnapshottos3setup,
      mock_loader):
    """Tests the process method, when the snapshots were provided via SetUp."""
    mock_copyebssnapshottos3teardown.return_value = None
    mock_copyebssnapshottos3process.side_effect = FAKE_EBS_COPY_PROCESS_RESPONSE
    mock_copyebssnapshottos3setup.return_value = FAKE_EBS_COPY_SETUP_RESPONSE
    mock_loader.return_value = None
    mock_sleep.return_value = None

    test_state = state.DFTimewolfState(config.Config)

    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)
    snaps_str = ','.join(
        [s['SnapshotId'] for s in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']])

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):
      collector.SetUp(snaps_str,
          FAKE_BUCKET,
          FAKE_REGION)

      collector.PreProcess()
      for c in collector.GetContainers(containers.AWSSnapshot):
        collector.Process(c)
      collector.PostProcess()

    actual_output = [c.path for c in \
        collector.GetContainers(containers.AWSS3Object)]

    self.assertEqual(sorted(actual_output), sorted([
          's3://fake-bucket/snap-01234567/image.bin',
          's3://fake-bucket/snap-01234567/log.txt',
          's3://fake-bucket/snap-01234567/hlog.txt',
          's3://fake-bucket/snap-01234567/mlog.txt',
          's3://fake-bucket/snap-12345678/image.bin',
          's3://fake-bucket/snap-12345678/log.txt',
          's3://fake-bucket/snap-12345678/hlog.txt',
          's3://fake-bucket/snap-12345678/mlog.txt']))

  # pylint: disable=line-too-long
  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.forensics.CopyEBSSnapshotToS3SetUp')
  @mock.patch('libcloudforensics.providers.aws.forensics.CopyEBSSnapshotToS3Process')
  @mock.patch('libcloudforensics.providers.aws.forensics.CopyEBSSnapshotToS3TearDown')
  @mock.patch('time.sleep', return_value=None)
  # pylint: enable=line-too-long
  def testProcessFromState(self,
      mock_sleep,
      mock_copyebssnapshottos3teardown,
      mock_copyebssnapshottos3process,
      mock_copyebssnapshottos3setup,
      mock_loader):
    """Tests the process method, when the snapshots were provided via State."""
    mock_copyebssnapshottos3teardown.return_value = None
    mock_copyebssnapshottos3process.side_effect = FAKE_EBS_COPY_PROCESS_RESPONSE
    mock_copyebssnapshottos3setup.return_value = FAKE_EBS_COPY_SETUP_RESPONSE
    mock_loader.return_value = None
    mock_sleep.return_value = None

    test_state = state.DFTimewolfState(config.Config)
    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)

    for snapshot in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']:
      collector.StoreContainer(containers.AWSSnapshot(
          snapshot['SnapshotId']))

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):
      collector.SetUp(None, FAKE_BUCKET, FAKE_REGION)

      collector.PreProcess()
      for c in collector.GetContainers(containers.AWSSnapshot):
        collector.Process(c)
      collector.PostProcess()

    actual_output = [c.path for c in \
        collector.GetContainers(containers.AWSS3Object)]

    self.assertEqual(sorted(actual_output), sorted([
          's3://fake-bucket/snap-01234567/image.bin',
          's3://fake-bucket/snap-01234567/log.txt',
          's3://fake-bucket/snap-01234567/hlog.txt',
          's3://fake-bucket/snap-01234567/mlog.txt',
          's3://fake-bucket/snap-12345678/image.bin',
          's3://fake-bucket/snap-12345678/log.txt',
          's3://fake-bucket/snap-12345678/hlog.txt',
          's3://fake-bucket/snap-12345678/mlog.txt']))


if __name__ == '__main__':
  unittest.main()
