#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GoogleCloudCollector."""

import unittest

import mock
import botocore

from libcloudforensics.providers.aws.internal import ec2
from libcloudforensics.providers.aws.internal import account as aws_account
from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.containers import aws_containers
from dftimewolf.lib.collectors import aws_snapshot_s3_copy


FAKE_BUCKET = "fake-bucket"
FAKE_SUBNET = "sub-01234567"
FAKE_REGION = 'fake-region-1'
FAKE_AZ_B = 'fake-region-1b'
FAKE_AZ_A = 'fake-region-1a'
with mock.patch('boto3.session.Session._setup_loader') as mock_session:
  mock_session.return_value = None
  FAKE_AWS_ACCOUNT = aws_account.AWSAccount(
      default_availability_zone=FAKE_AZ_A)

## Mirrors the responses from AWS APIs (minus unecessary fields)
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

def MockMakeAPICall(self, operation_name, kwarg):
  """Mock the boto3 api calls for specified client methods.

  Args:
    operation_name: The AWS API operation.
    kwarg: Args to pass to the method.
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
    """Tests that the collector can be initialised."""
    test_state = state.DFTimewolfState(config.Config)
    snapshots = 'snap-01234567,snap-12345678'

    # Subnet is optional - test with it.
    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)
    collector.SetUp(','.join([snapshot['SnapshotId']\
          for snapshot in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']]),
        FAKE_BUCKET,
        FAKE_REGION,
        FAKE_SUBNET)

    self.assertEqual(snapshots, collector.snapshots)
    self.assertEqual(FAKE_REGION, collector.region)
    self.assertEqual(FAKE_BUCKET, collector.bucket)
    self.assertEqual(FAKE_SUBNET, collector.subnet)

    # Subnet is optional - test without it.
    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)
    collector.SetUp(','.join([snapshot['SnapshotId']\
          for snapshot in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']]),
        FAKE_BUCKET,
        FAKE_REGION)

    self.assertEqual(snapshots, collector.snapshots)
    self.assertEqual(FAKE_REGION, collector.region)
    self.assertEqual(FAKE_BUCKET, collector.bucket)
    self.assertEqual(None, collector.subnet)

  @mock.patch('boto3.session.Session._setup_loader')
  def testPickAvailabilityZone(self, mock_loader):
    """Test the utility funciton that picks an anailability zone in the
    region to use."""
    mock_loader.return_value = None

    test_state = state.DFTimewolfState(config.Config)
    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)
    collector.SetUp(','.join([snapshot['SnapshotId']\
        for snapshot in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']]),
      FAKE_BUCKET,
      FAKE_REGION)

    with mock.patch('botocore.client.BaseClient._make_api_call',
      new=MockMakeAPICall):

      # Test without a subnet ID
      result = collector._PickAvailabilityZone()
      self.assertEqual(result, FAKE_AZ_A)

      # Test with a subnet ID
      result = collector._PickAvailabilityZone(FAKE_SUBNET)
      self.assertEqual(result, FAKE_AZ_B)

  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.forensics.CopyEBSSnapshotToS3')
  def testProcessFromParams(self, mock_copyebssnapshottos3, mock_loader):
    """Tests the process method, when the snapshots were provided via SetUp."""
    mock_copyebssnapshottos3.return_value = None
    mock_loader.return_value = None

    test_state = state.DFTimewolfState(config.Config)

    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)
    collector.SetUp(','.join([snapshot['SnapshotId']\
          for snapshot in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']]),
        FAKE_BUCKET,
        FAKE_REGION)

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):
      collector.Process()

    base_str = 's3://{0:s}/{1:s}'
    images = [aws_containers.S3Image(base_str.format(
        FAKE_BUCKET, snapshot['SnapshotId']) + '/image.bin',
      [
        base_str.format(FAKE_BUCKET, snapshot['SnapshotId']) + '/log.txt',
        base_str.format(FAKE_BUCKET, snapshot['SnapshotId']) + '/hlog.txt',
        base_str.format(FAKE_BUCKET, snapshot['SnapshotId']) + '/mlog.txt',
      ]
    ) for snapshot in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']]

    for image in images:
      self.assertIn(image, collector.state.GetContainers(
          aws_containers.AWSAttributeContainer)[0].s3_images)

  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.forensics.CopyEBSSnapshotToS3')
  def testProcessFromState(self, mock_copyebssnapshottos3, mock_loader):
    """Tests the process method, when the snapshots were provided via State."""
    mock_copyebssnapshottos3.return_value = None
    mock_loader.return_value = None

    container = aws_containers.AWSAttributeContainer()
    container.SetSnapshotIDs([snapshot['SnapshotId']\
        for snapshot in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']])
    test_state = state.DFTimewolfState(config.Config)
    test_state.StoreContainer(container)

    collector = aws_snapshot_s3_copy.AWSSnapshotS3CopyCollector(test_state)
    collector.SetUp(None, FAKE_BUCKET, FAKE_REGION)

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):
      collector.Process()

    base_str = 's3://{0:s}/{1:s}'
    images = [aws_containers.S3Image(base_str.format(
        FAKE_BUCKET, snapshot['SnapshotId']) + '/image.bin',
      [
        base_str.format(FAKE_BUCKET, snapshot['SnapshotId']) + '/log.txt',
        base_str.format(FAKE_BUCKET, snapshot['SnapshotId']) + '/hlog.txt',
        base_str.format(FAKE_BUCKET, snapshot['SnapshotId']) + '/mlog.txt',
      ]
    ) for snapshot in FAKE_DESCRIBE_SNAPSHOTS['Snapshots']]

    for image in images:
      self.assertIn(image, collector.state.GetContainers(
          aws_containers.AWSAttributeContainer)[0].s3_images)


if __name__ == '__main__':
  unittest.main()
