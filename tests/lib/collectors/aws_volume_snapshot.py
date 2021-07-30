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
from dftimewolf.lib.collectors import aws_volume_snapshot


FAKE_REGION = 'fake-region-1'
FAKE_AZ = 'fake_region-1b'
with mock.patch('boto3.session.Session._setup_loader') as mock_session:
  mock_session.return_value = None
  FAKE_AWS_ACCOUNT = aws_account.AWSAccount(
      default_availability_zone=FAKE_AZ)

FAKE_VOLUME_1 = {
  'AvailabilityZone': FAKE_AZ,
  'VolumeId': 'vol-01234567',
}
FAKE_VOLUME_2 = {
  'AvailabilityZone': FAKE_AZ,
  'VolumeId': 'vol-12345678',
}
FAKE_VOLUME_LIST = {
  'Volumes': [FAKE_VOLUME_1, FAKE_VOLUME_2]
}
FAKE_CREATE_SNAPSHOT_RESPONSE = {
  'SnapshotId': 'snap-01234567',
  'State': 'pending'
}
FAKE_DESCRIBE_SNAPSHOTS_RESPONSE = {
  'Snapshots': [{
    'SnapshotId': 'snap-01234567',
    'State': 'completed'
  }]
}

def MockMakeAPICall(self, operation_name, kwarg):
  """Mock the boto3 api calls for specified client methods.

  Args:
    operation_name: The AWS API operation.
    kwarg: Args to pass to the method.
  """
  if operation_name == 'DescribeVolumes':
    return FAKE_VOLUME_LIST
  if operation_name == 'CreateSnapshot':
    return FAKE_CREATE_SNAPSHOT_RESPONSE
  if operation_name == "DescribeSnapshots":
    return FAKE_DESCRIBE_SNAPSHOTS_RESPONSE
  # pylint: disable=protected-access
  return botocore.client.BaseClient._make_api_call(self, operation_name, kwarg)


class AWSVolumeSnapshotCollectorTest(unittest.TestCase):
  """Tests for the AWSVolumeSnapshotCollector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    collector = aws_volume_snapshot.AWSVolumeSnapshotCollector(test_state)
    self.assertIsNotNone(collector)

  def testSetUp(self):
    """Tests that the collector can be initialised."""
    test_state = state.DFTimewolfState(config.Config)
    volumes = 'vol-01234567,vol-12345678'

    collector = aws_volume_snapshot.AWSVolumeSnapshotCollector(test_state)
    collector.SetUp(','.join([volume['VolumeId']\
        for volume in FAKE_VOLUME_LIST['Volumes']]), FAKE_REGION)

    self.assertEqual(volumes, collector.volumes)
    self.assertEqual(FAKE_REGION, collector.region)

  @mock.patch('boto3.session.Session._setup_loader')
  def testProcessFromParams(self, mock_loader):
    """Tests the process method, when the volumes were provided via SetUp."""
    mock_loader.return_value = None

    test_state = state.DFTimewolfState(config.Config)

    collector = aws_volume_snapshot.AWSVolumeSnapshotCollector(test_state)
    collector.SetUp(','.join([volume['VolumeId']\
        for volume in FAKE_VOLUME_LIST['Volumes']]), FAKE_REGION)

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):
      collector.Process()

    self.assertEqual(len(collector.state.GetContainers(
        aws_containers.AWSAttributeContainer)), 1)
    self.assertEqual(collector.state.GetContainers(
        aws_containers.AWSAttributeContainer)[0].snapshots,
        ['snap-01234567', 'snap-01234567'])

  @mock.patch('boto3.session.Session._setup_loader')
  def testProcessFromState(self, mock_loader):
    """Tests the process method, when the volumes were provided via SetUp."""
    mock_loader.return_value = None

    container = aws_containers.AWSAttributeContainer()
    container.SetVolumeIDs([volume['VolumeId']\
        for volume in FAKE_VOLUME_LIST['Volumes']])
    test_state = state.DFTimewolfState(config.Config)
    test_state.StoreContainer(container)

    collector = aws_volume_snapshot.AWSVolumeSnapshotCollector(test_state)
    collector.SetUp(','.join([volume['VolumeId']\
        for volume in FAKE_VOLUME_LIST['Volumes']]), FAKE_REGION)

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):
      collector.Process()

    self.assertEqual(len(collector.state.GetContainers(
        aws_containers.AWSAttributeContainer)), 1)
    self.assertEqual(collector.state.GetContainers(
        aws_containers.AWSAttributeContainer)[0].snapshots,
        ['snap-01234567', 'snap-01234567'])


if __name__ == '__main__':
  unittest.main()
