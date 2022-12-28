#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the AzureCollector."""

from __future__ import unicode_literals

import unittest

import mock
from libcloudforensics.providers.azure.internal import account as az_account
from libcloudforensics.providers.azure.internal import compute

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.collectors import azure
from dftimewolf.lib.containers import containers


# pylint: disable=line-too-long
with mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials') as mock_creds:
  mock_creds.return_value = ('fake-subscription-id', mock.Mock())
  with mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup') as mock_resource:
    # pylint: enable=line-too-long
    mock_resource.return_value = 'fake-resource-group'
    FAKE_ACCOUNT = az_account.AZAccount(
        'fake-resource-group',
        default_region='fake-region'
    )
FAKE_ANALYSIS_VM = compute.AZComputeVirtualMachine(
    FAKE_ACCOUNT,
    '/subscriptions/id/resourceGroups/id/providers/Microsoft.Compute/VM/fake'
    '-instance-id',
    'fake-analysis-vm',
    'fake-region')
FAKE_INSTANCE = compute.AZComputeVirtualMachine(
    FAKE_ACCOUNT,
    '/subscriptions/id/resourceGroups/id/providers/Microsoft.Compute/VM/fake'
    '-owned-instance-id',
    'fake-owned-vm',
    'fake-region')
FAKE_DISK = compute.AZComputeDisk(
    FAKE_ACCOUNT,
    '/subscriptions/id/resourceGroups/id/providers/Microsoft.Compute/VM/fake'
    '-disk-id',
    'fake-disk',
    'fake-region')
FAKE_BOOT_DISK = compute.AZComputeDisk(
    FAKE_ACCOUNT,
    '/subscriptions/id/resourceGroups/id/providers/Microsoft.Compute/VM/fake'
    '-boot-disk-id',
    'fake-boot-disk',
    'fake-region')
FAKE_DISK_COPY = compute.AZComputeDisk(
    FAKE_ACCOUNT,
    '/subscriptions/id/resourceGroups/id/providers/Microsoft.Compute/VM/fake'
    '-boot-disk-copy-id',
    'fake-disk-copy',
    'fake-region')


class AzureCollectorTest(unittest.TestCase):
  """Tests for the Azure collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    azure_collector = azure.AzureCollector(test_state)
    self.assertIsNotNone(azure_collector)

  # pylint: disable=invalid-name, line-too-long
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup')
  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine')
  @mock.patch('libcloudforensics.providers.azure.forensics.StartAnalysisVm')
  def testSetUp1(self,
                 mock_StartAnalysisVm,
                 mock_AZVirtualMachine,
                 mock_GetCredentials,
                 mock_GetOrCreateResourceGroup):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    mock_GetCredentials.return_value = ('fake-subscription-id', mock.Mock())
    mock_StartAnalysisVm.return_value = (mock_AZVirtualMachine, None)
    mock_GetOrCreateResourceGroup.return_value = 'fake-resource-group'

    azure_collector = azure.AzureCollector(test_state)

    # Setup the collector with minimum information
    azure_collector.SetUp(
        'test-remote-profile-name',
        'test-analysis-resource-group-name',
        'fake_incident_id',
        'fake-ssh-public-key',
        remote_instance_name='fake-owned-vm'
    )
    self.assertEqual([], test_state.errors)
    self.assertEqual(
        'test-remote-profile-name', azure_collector.remote_profile_name)
    self.assertEqual('test-analysis-resource-group-name',
                     azure_collector.analysis_resource_group_name)
    self.assertEqual('fake_incident_id', azure_collector.incident_id)
    self.assertEqual([], azure_collector.disk_names)
    self.assertEqual(azure_collector.all_disks, False)
    self.assertEqual(
        'test-remote-profile-name', azure_collector.analysis_profile_name)

    mock_StartAnalysisVm.assert_called_with(
        'test-analysis-resource-group-name',
        'azure-forensics-vm-fake_incident_id',
        50,
        ssh_public_key='fake-ssh-public-key',
        cpu_cores=4,
        memory_in_mb=8192,
        region=None,
        dst_profile='test-remote-profile-name'
    )

  # pylint: disable=invalid-name, line-too-long
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup')
  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine')
  @mock.patch('libcloudforensics.providers.azure.forensics.StartAnalysisVm')
  def testSetUp2(self,
                 mock_StartAnalysisVm,
                 mock_AZVirtualMachine,
                 mock_GetCredentials,
                 mock_GetOrCreateResourceGroup):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    mock_GetCredentials.return_value = ('fake-subscription-id', mock.Mock())
    mock_StartAnalysisVm.return_value = (mock_AZVirtualMachine, None)
    mock_GetOrCreateResourceGroup.return_value = 'fake-resource-group'

    azure_collector = azure.AzureCollector(test_state)

    # Setup the collector with destination zone/profile and all_disks=True
    azure_collector.SetUp(
      'test-remote-profile-name',
      'test-analysis-resource-group-name',
      'fake_incident_id',
      'fake-ssh-public-key',
      remote_instance_name='fake-owned-vm',
      analysis_profile_name='test-analysis-profile-name',
      analysis_region='test-analysis-region',
      all_disks=True
    )
    self.assertEqual([], test_state.errors)
    self.assertEqual(
      'test-remote-profile-name', azure_collector.remote_profile_name)
    self.assertEqual('test-analysis-resource-group-name',
                     azure_collector.analysis_resource_group_name)
    self.assertEqual('fake_incident_id', azure_collector.incident_id)
    self.assertEqual([], azure_collector.disk_names)
    self.assertEqual(azure_collector.all_disks, True)
    self.assertEqual(
      'test-analysis-profile-name', azure_collector.analysis_profile_name)
    self.assertEqual('test-analysis-region', azure_collector.analysis_region)

    mock_StartAnalysisVm.assert_called_with(
        'test-analysis-resource-group-name',
        'azure-forensics-vm-fake_incident_id',
        50,
        ssh_public_key='fake-ssh-public-key',
        cpu_cores=4,
        memory_in_mb=8192,
        region='test-analysis-region',
        dst_profile='test-analysis-profile-name'
    )

  # pylint: disable=invalid-name, line-too-long
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup')
  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')
  @mock.patch('libcloudforensics.providers.azure.forensics.StartAnalysisVm')
  @mock.patch('libcloudforensics.providers.azure.forensics.CreateDiskCopy')
  @mock.patch('dftimewolf.lib.collectors.azure.AzureCollector._FindDisksToCopy')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine.AttachDisk')
  def testProcess(self,
                  unused_mock_AttachDisk,
                  mock_FindVolumesToCopy,
                  mock_CreateDiskCopy,
                  mock_StartAnalysisVm,
                  mock_GetCredentials,
                  mock_GetOrCreateResourceGroup):
    """Tests the collector's Process() function."""
    mock_StartAnalysisVm.return_value = (FAKE_ANALYSIS_VM, None)
    mock_FindVolumesToCopy.return_value = [FAKE_DISK]
    mock_CreateDiskCopy.return_value = FAKE_DISK_COPY
    mock_GetCredentials.return_value = ('fake-subscription-id', mock.Mock())
    mock_GetOrCreateResourceGroup.return_value = 'fake-resource-group'

    test_state = state.DFTimewolfState(config.Config)
    azure_collector = azure.AzureCollector(test_state)
    # Setup the collector with destination zone and all_disks=True
    azure_collector.SetUp(
      'test-remote-profile-name',
      'test-analysis-resource-group-name',
      'fake_incident_id',
      'fake-ssh-public-key',
      remote_instance_name='fake-owned-vm',
      analysis_profile_name='test-analysis-profile-name',
      analysis_region='test-analysis-region',
      all_disks=True
    )
    azure_collector.Process()

    mock_CreateDiskCopy.assert_called_with(
        'test-analysis-resource-group-name',
        disk_name='fake-disk',
        region='test-analysis-region',
        src_profile='test-remote-profile-name',
        dst_profile='test-analysis-profile-name')
    forensics_vms = azure_collector.GetContainers(containers.ForensicsVM)
    forensics_vm = forensics_vms[0]
    self.assertEqual('fake-analysis-vm', forensics_vm.name)
    self.assertEqual(
        'fake-disk-copy', forensics_vm.evidence_disk.name)

  # pylint: disable=invalid-name, line-too-long
  @mock.patch('libcloudforensics.providers.azure.internal.resource.AZResource.GetOrCreateResourceGroup')
  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine.GetBootDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZComputeVirtualMachine.ListDisks')
  @mock.patch('libcloudforensics.providers.azure.internal.compute.AZCompute.GetInstance')
  # We're manually calling protected functions
  # pylint: disable=protected-access, invalid-name
  def testFindDisksToCopy(self,
                          mock_GetInstance,
                          mock_ListDisks,
                          mock_GetDisk,
                          mock_GetBootDisk,
                          mock_GetCredentials,
                          mock_GetOrCreateResourceGroup):
    """Tests the FindDisksToCopy function with different SetUp() calls."""
    test_state = state.DFTimewolfState(config.Config)
    azure_collector = azure.AzureCollector(test_state)
    mock_ListDisks.return_value = {
        FAKE_BOOT_DISK.name: FAKE_BOOT_DISK,
        FAKE_DISK.name: FAKE_DISK
    }
    mock_GetDisk.return_value = FAKE_DISK
    mock_GetInstance.return_value = FAKE_INSTANCE
    mock_GetBootDisk.return_value = FAKE_BOOT_DISK
    mock_GetCredentials.return_value = ('fake-subscription-id', mock.Mock())
    mock_GetOrCreateResourceGroup.return_value = 'fake-resource-group'

    # Nothing is specified, AzureCollector should collect the instance's
    # boot disk
    azure_collector.SetUp(
        'test-remote-profile-name',
        'test-analysis-resource-group-name',
        'fake_incident_id',
        'fake-ssh-public-key',
        remote_instance_name='fake-owned-vm'
    )
    disks = azure_collector._FindDisksToCopy()
    self.assertEqual(1, len(disks))
    self.assertEqual('fake-boot-disk', disks[0].name)
    mock_GetInstance.assert_called_with('fake-owned-vm')
    mock_GetBootDisk.assert_called_once()
    mock_ListDisks.assert_not_called()

    # Specifying all_disks should return all disks for the instance
    # (see mock_ListDisks return value)
    azure_collector.SetUp(
        'test-remote-profile-name',
        'test-analysis-resource-group-name',
        'fake_incident_id',
        'fake-ssh-public-key',
        remote_instance_name='fake-owned-vm',
        all_disks=True
    )
    disks = azure_collector._FindDisksToCopy()
    self.assertEqual(2, len(disks))
    self.assertEqual('fake-boot-disk', disks[0].name)
    self.assertEqual('fake-disk', disks[1].name)
    mock_ListDisks.assert_called_once()

    # If a list of 1 disk ID is passed, that disk only should be returned
    azure_collector.SetUp(
        'test-remote-profile-name',
        'test-analysis-resource-group-name',
        'fake_incident_id',
        'fake-ssh-public-key',
        remote_instance_name='',
        disk_names='fake-disk'
    )
    disks = azure_collector._FindDisksToCopy()
    self.assertEqual(1, len(disks))
    self.assertEqual('fake-disk', disks[0].name)
    mock_GetDisk.assert_called_once()

if __name__ == '__main__':
  unittest.main()
