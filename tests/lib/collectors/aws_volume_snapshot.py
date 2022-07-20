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
from dftimewolf.lib.collectors import aws_volume_snapshot


FAKE_REGION = 'fake-region-1'
FAKE_AZ = 'fake_region-1b'
with mock.patch('boto3.session.Session._setup_loader') as mock_session:
  mock_session.return_value = None
  FAKE_AWS_ACCOUNT = aws_account.AWSAccount(
      default_availability_zone=FAKE_AZ)

# Mirrors the responses from AWS APIs (minus unnecessary fields)
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
FAKE_VOLUME_LIST_STR = '{0:s},{1:s}'.format(
    FAKE_VOLUME_1['VolumeId'],
    FAKE_VOLUME_2['VolumeId'])
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

# pylint: disable=protected-access
orig = botocore.client.BaseClient._make_api_call

def MockMakeAPICall(self, operation_name : str, kwarg : Any) -> Any:
  """Mock the boto3 api calls for specified client methods.

  Args:
    operation_name: The AWS API operation.
    kwarg: Args to pass to the method.

  Returns:
    The result of a mock API call, if available.
  """
  if operation_name == 'DescribeVolumes':
    return FAKE_VOLUME_LIST
  if operation_name == 'CreateSnapshot':
    return FAKE_CREATE_SNAPSHOT_RESPONSE
  if operation_name == 'DescribeSnapshots':
    return FAKE_DESCRIBE_SNAPSHOTS_RESPONSE
  return orig(self, operation_name, kwarg)


class AWSVolumeSnapshotCollectorTest(unittest.TestCase):
  """Tests for the AWSVolumeSnapshotCollector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    collector = aws_volume_snapshot.AWSVolumeSnapshotCollector(test_state)
    self.assertIsNotNone(collector)

  def testSetUp(self):
    """Tests SetUp of the collector."""
    test_state = state.DFTimewolfState(config.Config)

    collector = aws_volume_snapshot.AWSVolumeSnapshotCollector(test_state)
    collector.SetUp(FAKE_VOLUME_LIST_STR, FAKE_REGION)

    volumes_in_state = [container.id for container in \
        test_state.GetContainers(containers.AWSVolume)]

    self.assertEqual(['vol-01234567', 'vol-12345678'], volumes_in_state)
    self.assertEqual(FAKE_REGION, collector.region)

  @mock.patch('time.sleep')
  @mock.patch('boto3.session.Session._setup_loader')
  def testProcessFromParams(self, mock_loader, mock_sleep):
    """Tests the process method, when the volumes were provided via SetUp."""
    mock_loader.return_value = None
    mock_sleep.return_value = None

    test_state = state.DFTimewolfState(config.Config)

    collector = aws_volume_snapshot.AWSVolumeSnapshotCollector(test_state)
    collector.SetUp(FAKE_VOLUME_LIST_STR, FAKE_REGION)

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):
      collector.Process()

    self.assertEqual(2, len(test_state.GetContainers(
        containers.AWSSnapshot)))
    state_snaps = [c.id for c in test_state.GetContainers(
        containers.AWSSnapshot)]
    self.assertEqual(state_snaps, ['snap-01234567', 'snap-01234567'])

  @mock.patch('time.sleep')
  @mock.patch('boto3.session.Session._setup_loader')
  def testProcessFromState(self, mock_loader, mock_sleep):
    """Tests the process method, when the volumes were provided via state."""
    mock_loader.return_value = None
    mock_sleep.return_value = None

    test_state = state.DFTimewolfState(config.Config)
    for volume in FAKE_VOLUME_LIST['Volumes']:
      test_state.StoreContainer(containers.AWSVolume(volume['VolumeId']))

    collector = aws_volume_snapshot.AWSVolumeSnapshotCollector(test_state)
    collector.SetUp(None, FAKE_REGION)

    with mock.patch('botocore.client.BaseClient._make_api_call',
        new=MockMakeAPICall):
      collector.Process()

    self.assertEqual(2, len(test_state.GetContainers(
        containers.AWSSnapshot)))
    state_snaps = [c.id for c in test_state.GetContainers(
        containers.AWSSnapshot)]
    self.assertEqual(state_snaps, ['snap-01234567', 'snap-01234567'])


if __name__ == '__main__':
  unittest.main()
