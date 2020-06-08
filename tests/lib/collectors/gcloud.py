#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GoogleCloudCollector."""

import unittest

import mock
from libcloudforensics import gcp

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.collectors import gcloud

FAKE_PROJECT = gcp.GoogleCloudProject(
    'test-target-project-name',
    'fake_zone')
FAKE_ANALYSIS_VM = gcp.GoogleComputeInstance(
    FAKE_PROJECT,
    'fake_zone',
    'fake-analysis-vm')
FAKE_INSTANCE = gcp.GoogleComputeInstance(
    FAKE_PROJECT,
    'fake_zone',
    'fake-instance')
FAKE_DISK = gcp.GoogleComputeDisk(
    FAKE_PROJECT,
    'fake_zone',
    'disk1')
FAKE_BOOT_DISK = gcp.GoogleComputeDisk(
    FAKE_PROJECT,
    'fake_zone',
    'bootdisk')
FAKE_SNAPSHOT = gcp.GoogleComputeSnapshot(
    FAKE_DISK,
    FAKE_PROJECT)
FAKE_DISK_COPY = gcp.GoogleComputeDisk(
    FAKE_PROJECT,
    'fake_zone',
    'disk1-copy')

def ReturnFakeDisk(disk_name):
  """Generate fake GoogleCloudComputeDisk objects depending on provided name."""
  return gcp.GoogleComputeDisk(
      FAKE_PROJECT, 'fakezone', disk_name)


class GoogleCloudCollectorTest(unittest.TestCase):
  """Tests for the GCloud collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    gcloud_collector = gcloud.GoogleCloudCollector(test_state)
    self.assertIsNotNone(gcloud_collector)

  # pylint: disable=invalid-name
  @mock.patch(
      'libcloudforensics.gcp.GoogleComputeBaseResource.AddLabels')
  @mock.patch('libcloudforensics.gcp.GoogleComputeBaseResource')
  @mock.patch('libcloudforensics.gcp.StartAnalysisVm')
  def testSetUp(self,
                mock_StartAnalysisVm,
                mock_GoogleComputeBaseResource,
                mock_AddLabels):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    mock_StartAnalysisVm.return_value = (mock_GoogleComputeBaseResource, None)

    gcloud_collector = gcloud.GoogleCloudCollector(test_state)
    gcloud_collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_incident_id',
        'fake_zone',
        'pd-standard',
        42.0,
        16,
        remote_instance_name='my-owned-instance',
    )
    self.assertEqual(test_state.errors, [])
    self.assertEqual(gcloud_collector.disk_names, [])
    self.assertEqual(gcloud_collector.analysis_project.project_id,
                     'test-analysis-project-name')
    self.assertEqual(gcloud_collector.remote_project.project_id,
                     'test-target-project-name')
    self.assertEqual(gcloud_collector.remote_instance_name,
                     'my-owned-instance')
    self.assertEqual(gcloud_collector.all_disks, False)

    mock_StartAnalysisVm.assert_called_with(
        'test-analysis-project-name',
        'gcp-forensics-vm-fake_incident_id',
        'fake_zone',
        'pd-standard',
        42.0,
        16,
        attach_disk=None,
        image_family='ubuntu-1804-lts',
        image_project='ubuntu-os-cloud'
    )
    mock_AddLabels.assert_has_calls(
        [mock.call({'incident_id': 'fake_incident_id'})])

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.gcp.GoogleComputeBaseResource.AddLabels')
  @mock.patch('libcloudforensics.gcp.StartAnalysisVm')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.CreateDiskFromSnapshot')
  @mock.patch('dftimewolf.lib.collectors.gcloud.GoogleCloudCollector._FindDisksToCopy')
  @mock.patch('libcloudforensics.gcp.GoogleComputeDisk.Snapshot')
  @mock.patch('libcloudforensics.gcp.GoogleComputeSnapshot.Delete')
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.AttachDisk')
  def testProcess(self,
                  unused_MockAttachDisk,
                  mock_Delete,
                  mock_Snapshot,
                  mock_FindDisks,
                  mock_CreateDiskFromSnapshot,
                  mock_StartAnalysisVm,
                  mock_AddLabels,
                  mock_GetBootDisk):
    """Tests the collector's Process() function."""
    mock_StartAnalysisVm.return_value = (FAKE_ANALYSIS_VM, None)
    mock_FindDisks.return_value = [
        gcp.GoogleComputeDisk(
            FAKE_PROJECT,
            'fake_zone',
            'disk1')
    ]
    mock_CreateDiskFromSnapshot.return_value = FAKE_DISK_COPY
    mock_Snapshot.return_value = FAKE_SNAPSHOT
    FAKE_ANALYSIS_VM.AddLabels = mock_AddLabels
    FAKE_ANALYSIS_VM.GetBootDisk = mock_GetBootDisk
    FAKE_DISK_COPY.AddLabels = mock_AddLabels

    test_state = state.DFTimewolfState(config.Config)
    gcloud_collector = gcloud.GoogleCloudCollector(test_state)
    gcloud_collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_incident_id',
        'fake_zone',
        'pd-standard',
        42.0,
        16,
        remote_instance_name='my-owned-instance',
    )
    gcloud_collector.Process()

    mock_Snapshot.assert_called_once()
    mock_CreateDiskFromSnapshot.assert_called_with(
        FAKE_SNAPSHOT, disk_name_prefix='incidentfake_incident_id')
    mock_Delete.assert_called_once()
    self.assertEqual(test_state.output[0][0], 'fake-analysis-vm')
    self.assertEqual(test_state.output[0][1].name, 'disk1-copy')
    mock_AddLabels.assert_has_calls([mock.call({'incident_id': 'fake_incident_id'})])

  # pylint: disable=line-too-long,invalid-name
  @mock.patch('libcloudforensics.gcp.GoogleComputeBaseResource')
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GetDisk')
  @mock.patch('libcloudforensics.gcp.GoogleComputeInstance.ListDisks')
  @mock.patch('libcloudforensics.gcp.GoogleCloudProject.GetInstance')
  @mock.patch('libcloudforensics.gcp.StartAnalysisVm')
  # We're manually calling protected functions
  # pylint: disable=protected-access
  def testFindDisksToCopy(self,
                          mock_StartAnalysisVm,
                          mock_get_instance,
                          mock_list_disks,
                          mock_get_disk,
                          mock_GetBootDisk,
                          mock_GoogleComputeBaseResource):
    """Tests the FindDisksToCopy function with different SetUp() calls."""
    test_state = state.DFTimewolfState(config.Config)
    gcloud_collector = gcloud.GoogleCloudCollector(test_state)
    mock_StartAnalysisVm.return_value = (mock_GoogleComputeBaseResource, None)
    mock_list_disks.return_value = ['bootdisk', 'disk1']
    mock_get_disk.side_effect = ReturnFakeDisk
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_GetBootDisk.return_value = FAKE_BOOT_DISK

    # Nothing is specified, GoogleCloudCollector should collect the instance's
    # boot disk
    gcloud_collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_incident_id',
        'fake_zone',
        'pd-standard',
        42.0,
        16,
        remote_instance_name='my-owned-instance',
    )
    disks = gcloud_collector._FindDisksToCopy()
    self.assertEqual(len(disks), 1)
    self.assertEqual(disks[0].name, 'bootdisk')
    mock_GetBootDisk.assert_called_once()

    # Specifying all_disks should return all disks for the instance
    # (see mock_list_disks return value)
    gcloud_collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_incident_id',
        'fake_zone',
        'pd-standard',
        42.0,
        16,
        remote_instance_name='my-owned-instance',
        all_disks=True
    )
    disks = gcloud_collector._FindDisksToCopy()
    self.assertEqual(len(disks), 2)
    self.assertEqual(disks[0].name, 'bootdisk')
    self.assertEqual(disks[1].name, 'disk1')

    # If a list of disks is passed, that disk only should be returned
    gcloud_collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_incident_id',
        'fake_zone',
        'pd-standard',
        42.0,
        16,
        remote_instance_name='my-owned-instance',
        disk_names='disk1'
    )
    disks = gcloud_collector._FindDisksToCopy()
    self.assertEqual(len(disks), 1)
    self.assertEqual(disks[0].name, 'disk1')


if __name__ == '__main__':
  unittest.main()
