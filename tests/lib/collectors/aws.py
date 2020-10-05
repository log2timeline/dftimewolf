#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the AWSCollector."""

from __future__ import unicode_literals

import unittest

import mock
from libcloudforensics.providers.aws.internal import account as aws_account
from libcloudforensics.providers.aws.internal import ebs, ec2

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.collectors import aws
from dftimewolf.lib.containers import containers

with mock.patch('boto3.session.Session._setup_loader') as mock_session:
  mock_session.return_value = None
  FAKE_AWS_ACCOUNT = aws_account.AWSAccount(
      default_availability_zone='fake-zone-2b')
FAKE_ANALYSIS_VM = ec2.AWSInstance(
    FAKE_AWS_ACCOUNT,
    'fake-analysis-vm-id',
    'fake-zone-2',
    'fake-zone-2b',
    name='fake-analysis-vm')
FAKE_INSTANCE = ec2.AWSInstance(
    FAKE_AWS_ACCOUNT,
    'my-owned-instance-id',
    'fake-zone-2',
    'fake-zone-2b')
FAKE_VOLUME = ebs.AWSVolume(
    'fake-volume-id',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b',
    False)
FAKE_BOOT_VOLUME = ebs.AWSVolume(
    'fake-boot-volume-id',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b',
    False,
    name='fake-boot-volume',
    device_name='/dev/spf')
FAKE_VOLUME_COPY = ebs.AWSVolume(
    'fake-volume-id-copy',
    FAKE_AWS_ACCOUNT,
    'fake-zone-2',
    'fake-zone-2b',
    False)


class AWSCollectorTest(unittest.TestCase):
  """Tests for the AWS collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    gcloud_collector = aws.AWSCollector(test_state)
    self.assertIsNotNone(gcloud_collector)

  # pylint: disable=invalid-name
  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.AWSInstance')
  @mock.patch('libcloudforensics.providers.aws.forensics.StartAnalysisVm')
  def testSetUp1(self, mock_StartAnalysisVm, mock_AWSInstance, mock_loader):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    mock_StartAnalysisVm.return_value = (mock_AWSInstance, None)
    mock_loader.return_value = None

    aws_collector = aws.AWSCollector(test_state)

    # Setup the collector with minimum information
    aws_collector.SetUp(
        'test-remote-profile-name',
        'test-remote-zone',
        'fake_incident_id',
        remote_instance_id='my-owned-instance-id'
    )
    self.assertEqual([], test_state.errors)
    self.assertEqual(
        'test-remote-profile-name', aws_collector.remote_profile_name)
    self.assertEqual('test-remote-zone', aws_collector.remote_zone)
    self.assertEqual('fake_incident_id', aws_collector.incident_id)
    self.assertEqual([], aws_collector.volume_ids)
    self.assertEqual(aws_collector.all_volumes, False)
    self.assertEqual(
        'test-remote-profile-name', aws_collector.analysis_profile_name)
    self.assertEqual('test-remote-zone', aws_collector.analysis_zone)

    mock_StartAnalysisVm.assert_called_with(
        'aws-forensics-vm-fake_incident_id',
        'test-remote-zone',
        50,
        ami=None,
        cpu_cores=16,
        dst_profile='test-remote-profile-name'
    )

  # pylint: disable=invalid-name
  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.forensics.StartAnalysisVm')
  def testSetUp2(self, mock_StartAnalysisVm, mock_loader):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    mock_StartAnalysisVm.return_value = (FAKE_INSTANCE, None)
    mock_loader.return_value = None

    aws_collector = aws.AWSCollector(test_state)

    # Setup the collector with an instance ID, destination zone and profile.
    aws_collector.SetUp(
        'test-remote-profile-name',
        'test-remote-zone',
        'fake_incident_id',
        remote_instance_id='my-owned-instance-id',
        all_volumes=True,
        analysis_profile_name='test-analysis-profile-name',
        analysis_zone='test-analysis-zone'
    )
    self.assertEqual([], test_state.errors)
    self.assertEqual(
        'test-remote-profile-name', aws_collector.remote_profile_name)
    self.assertEqual('test-remote-zone', aws_collector.remote_zone)
    self.assertEqual('fake_incident_id', aws_collector.incident_id)
    self.assertEqual([], aws_collector.volume_ids)
    self.assertEqual(aws_collector.all_volumes, True)
    self.assertEqual('my-owned-instance-id', aws_collector.remote_instance_id)
    self.assertEqual(
        'test-analysis-profile-name', aws_collector.analysis_profile_name)
    self.assertEqual('test-analysis-zone', aws_collector.analysis_zone)

    mock_StartAnalysisVm.assert_called_with(
        'aws-forensics-vm-fake_incident_id',
        'test-analysis-zone',
        50,
        ami=None,
        cpu_cores=16,
        dst_profile='test-analysis-profile-name'
    )

  # pylint: disable=line-too-long, invalid-name
  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.forensics.StartAnalysisVm')
  @mock.patch('libcloudforensics.providers.aws.forensics.CreateVolumeCopy')
  @mock.patch('dftimewolf.lib.collectors.aws.AWSCollector._FindVolumesToCopy')
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.AWSInstance.AttachVolume')
  def testProcess(self,
                  unused_mock_AttachVolume,
                  mock_FindVolumesToCopy,
                  mock_CreateVolumeCopy,
                  mock_StartAnalysisVm,
                  mock_loader):
    """Tests the collector's Process() function."""
    mock_StartAnalysisVm.return_value = (FAKE_ANALYSIS_VM, None)
    mock_FindVolumesToCopy.return_value = [FAKE_VOLUME]
    mock_CreateVolumeCopy.return_value = FAKE_VOLUME_COPY
    mock_loader.return_value = None

    test_state = state.DFTimewolfState(config.Config)
    aws_collector = aws.AWSCollector(test_state)
    aws_collector.SetUp(
        'test-remote-profile-name',
        'test-remote-zone',
        'fake_incident_id',
        remote_instance_id='my-owned-instance-id',
        all_volumes=True,
        analysis_profile_name='test-analysis-profile-name',
        analysis_zone='test-analysis-zone'
    )
    aws_collector.Process()

    mock_CreateVolumeCopy.assert_called_with(
        'test-remote-zone',
        dst_zone='test-analysis-zone',
        volume_id=FAKE_VOLUME.volume_id,
        src_profile='test-remote-profile-name',
        dst_profile='test-analysis-profile-name')
    forensics_vms = test_state.GetContainers(containers.ForensicsVM)
    forensics_vm = forensics_vms[0]
    self.assertEqual('fake-analysis-vm', forensics_vm.name)
    self.assertEqual(
        'fake-volume-id-copy', forensics_vm.evidence_disk.volume_id)

  # pylint: disable=line-too-long
  @mock.patch('boto3.session.Session._setup_loader')
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.AWSInstance.GetBootVolume')
  @mock.patch('libcloudforensics.providers.aws.internal.ebs.EBS.GetVolumeById')
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.AWSInstance.ListVolumes')
  @mock.patch('libcloudforensics.providers.aws.internal.ec2.EC2.GetInstanceById')
  @mock.patch('libcloudforensics.providers.aws.forensics.StartAnalysisVm')
  # We're manually calling protected functions
  # pylint: disable=protected-access, invalid-name
  def testFindVolumesToCopy(self,
                            mock_StartAnalysisVm,
                            mock_GetInstanceById,
                            mock_ListVolumes,
                            mock_GetVolumeById,
                            mock_GetBootVolume,
                            mock_loader):
    """Tests the FindVolumesToCopy function with different SetUp() calls."""
    test_state = state.DFTimewolfState(config.Config)
    aws_collector = aws.AWSCollector(test_state)
    mock_StartAnalysisVm.return_value = (FAKE_INSTANCE, None)
    mock_loader.return_value = None
    mock_ListVolumes.return_value = {
        FAKE_BOOT_VOLUME.volume_id: FAKE_BOOT_VOLUME,
        FAKE_VOLUME.volume_id: FAKE_VOLUME
    }
    mock_GetVolumeById.return_value = FAKE_VOLUME
    mock_GetInstanceById.return_value = FAKE_INSTANCE
    mock_GetBootVolume.return_value = FAKE_BOOT_VOLUME

    # Nothing is specified, AWSCollector should collect the instance's
    # boot volume
    aws_collector.SetUp(
        'test-remote-profile-name',
        'test-remote-zone',
        'fake_incident_id',
        remote_instance_id='my-owned-instance-id'
    )
    volumes = aws_collector._FindVolumesToCopy()
    self.assertEqual(1, len(volumes))
    self.assertEqual('fake-boot-volume-id', volumes[0].volume_id)
    mock_GetInstanceById.assert_called_once()
    mock_GetBootVolume.assert_called_once()
    mock_ListVolumes.assert_not_called()

    # Specifying all_volumes should return all volumes for the instance
    # (see mock_ListVolumes return value)
    aws_collector.SetUp(
        'test-remote-profile-name',
        'test-remote-zone',
        'fake_incident_id',
        remote_instance_id='my-owned-instance-id',
        all_volumes=True
    )
    volumes = aws_collector._FindVolumesToCopy()
    self.assertEqual(2, len(volumes))
    self.assertEqual('fake-boot-volume-id', volumes[0].volume_id)
    self.assertEqual('fake-volume-id', volumes[1].volume_id)
    mock_ListVolumes.assert_called_once()

    # If a list of 1 volume ID is passed, that volume only should be returned
    aws_collector.SetUp(
        'test-remote-profile-name',
        'test-remote-zone',
        'fake_incident_id',
        remote_instance_id='',
        volume_ids=FAKE_VOLUME.volume_id
    )
    volumes = aws_collector._FindVolumesToCopy()
    self.assertEqual(1, len(volumes))
    self.assertEqual('fake-volume-id', volumes[0].volume_id)
    mock_GetVolumeById.assert_called_once()

if __name__ == '__main__':
  unittest.main()
