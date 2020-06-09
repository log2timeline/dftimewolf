#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GoogleCloudCollector."""

import unittest

import mock
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute_resources

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.collectors import gcloud

FAKE_PROJECT = gcp_project.GoogleCloudProject(
    'test-target-project-name',
    'fake_zone')
FAKE_ANALYSIS_VM = compute_resources.GoogleComputeInstance(
    FAKE_PROJECT.project_id,
    'fake_zone',
    'fake-analysis-vm')
FAKE_INSTANCE = compute_resources.GoogleComputeInstance(
    FAKE_PROJECT.project_id,
    'fake_zone',
    'fake-instance')
FAKE_DISK = compute_resources.GoogleComputeDisk(
    FAKE_PROJECT.project_id,
    'fake_zone',
    'disk1')
FAKE_BOOT_DISK = compute_resources.GoogleComputeDisk(
    FAKE_PROJECT.project_id,
    'fake_zone',
    'bootdisk')
FAKE_SNAPSHOT = compute_resources.GoogleComputeSnapshot(
    FAKE_DISK,
    'fake_snapshot')
FAKE_DISK_COPY = compute_resources.GoogleComputeDisk(
    FAKE_PROJECT.project_id,
    'fake_zone',
    'disk1-copy')


class GoogleCloudCollectorTest(unittest.TestCase):
  """Tests for the GCloud collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    gcloud_collector = gcloud.GoogleCloudCollector(test_state)
    self.assertIsNotNone(gcloud_collector)

  # pylint: disable=invalid-name,line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.compute_resources.GoogleComputeBaseResource.AddLabels')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute_resources.GoogleComputeBaseResource')
  @mock.patch('libcloudforensics.providers.gcp.forensics.StartAnalysisVm')
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
        image_family='ubuntu-1804-lts',
        image_project='ubuntu-os-cloud'
    )
    mock_AddLabels.assert_has_calls(
        [mock.call({'incident_id': 'fake_incident_id'})])

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.compute_resources.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute_resources.GoogleComputeBaseResource.AddLabels')
  @mock.patch('libcloudforensics.providers.gcp.forensics.StartAnalysisVm')
  @mock.patch('libcloudforensics.providers.gcp.forensics.CreateDiskCopy')
  @mock.patch('dftimewolf.lib.collectors.gcloud.GoogleCloudCollector._FindDisksToCopy')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute_resources.GoogleComputeInstance.AttachDisk')
  def testProcess(self,
                  unused_MockAttachDisk,
                  mock_FindDisks,
                  mock_CreateDiskCopy,
                  mock_StartAnalysisVm,
                  mock_AddLabels,
                  mock_GetBootDisk):
    """Tests the collector's Process() function."""
    mock_StartAnalysisVm.return_value = (FAKE_ANALYSIS_VM, None)
    mock_FindDisks.return_value = [FAKE_DISK]
    mock_CreateDiskCopy.return_value = FAKE_DISK_COPY
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

    mock_CreateDiskCopy.assert_called_with(
        'test-target-project-name',
        'test-analysis-project-name',
        None,
        FAKE_DISK.zone,
        disk_name=FAKE_DISK.name)
    forensics_vms = test_state.GetContainers(containers.ForensicsVM)
    self.assertEqual(forensics_vms[0].name, 'fake-analysis-vm')
    self.assertEqual(forensics_vms[0].evidence_disk.name, 'disk1-copy')
    mock_AddLabels.assert_has_calls([mock.call({'incident_id': 'fake_incident_id'})])

  # pylint: disable=line-too-long,invalid-name
  @mock.patch('libcloudforensics.providers.gcp.internal.compute_resources.GoogleComputeBaseResource')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute_resources.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute_resources.GoogleComputeInstance.ListDisks')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetInstance')
  @mock.patch('libcloudforensics.providers.gcp.forensics.StartAnalysisVm')
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
    mock_list_disks.return_value = {
        'bootdisk': FAKE_BOOT_DISK,
        'disk1': FAKE_DISK
    }
    mock_get_disk.return_value = FAKE_DISK
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
