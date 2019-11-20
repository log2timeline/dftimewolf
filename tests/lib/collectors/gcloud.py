#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GoogleCloudCollector."""

from __future__ import unicode_literals

import unittest

import mock
from turbinia.lib import libcloudforensics

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.collectors import gcloud

FAKE_PROJECT = libcloudforensics.GoogleCloudProject(
    'test-target-project-name',
    'fake_zone')
FAKE_ANALYSIS_VM = libcloudforensics.GoogleComputeInstance(
    FAKE_PROJECT,
    'fake_zone',
    'fake-analysis-vm')
FAKE_INSTANCE = libcloudforensics.GoogleComputeInstance(
    FAKE_PROJECT,
    'fake_zone',
    'fake-instance')
FAKE_DISK = libcloudforensics.GoogleComputeDisk(
    FAKE_PROJECT,
    'fake_zone',
    'disk1')
FAKE_BOOT_DISK = libcloudforensics.GoogleComputeDisk(
    FAKE_PROJECT,
    'fake_zone',
    'bootdisk')
FAKE_SNAPSHOT = libcloudforensics.GoogleComputeSnapshot(
    FAKE_DISK,
    FAKE_PROJECT)
FAKE_DISK_COPY = libcloudforensics.GoogleComputeDisk(
    FAKE_PROJECT,
    'fake_zone',
    'disk1-copy')

def ReturnFakeDisk(disk_name):
  """Generate fake GoogleCloudComputeDisk objects depending on provided name."""
  return libcloudforensics.GoogleComputeDisk(
      FAKE_PROJECT, 'fakezone', disk_name)


class GoogleCloudCollectorTest(unittest.TestCase):
  """Tests for the Stackdriver collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    gcloud_collector = gcloud.GoogleCloudCollector(test_state)
    self.assertIsNotNone(gcloud_collector)

  @mock.patch(
      'turbinia.lib.libcloudforensics.GoogleComputeBaseResource.add_labels')
  @mock.patch('turbinia.lib.libcloudforensics.GoogleComputeBaseResource')
  @mock.patch('turbinia.lib.libcloudforensics.start_analysis_vm')
  def testSetUp(self,
                mock_start_analysis_vm,
                mock_GoogleComputeBaseResource,
                mock_add_labels):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    mock_start_analysis_vm.return_value = (mock_GoogleComputeBaseResource, None)

    gcloud_collector = gcloud.GoogleCloudCollector(test_state)
    gcloud_collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_incident_id',
        'fake_zone',
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

    mock_start_analysis_vm.assert_called_with(
        'test-analysis-project-name',
        'gcp-forensics-vm-fake_incident_id',
        'fake_zone',
        42.0,
        16,
        attach_disk=None,
        image_family='ubuntu-1804-lts',
        image_project='ubuntu-os-cloud'
    )
    mock_add_labels.assert_has_calls(
        [mock.call({'incident_id': 'fake_incident_id'})])

  # pylint: disable=line-too-long
  @mock.patch('turbinia.lib.libcloudforensics.GoogleComputeInstance.get_boot_disk')
  @mock.patch('turbinia.lib.libcloudforensics.GoogleComputeBaseResource.add_labels')
  @mock.patch('turbinia.lib.libcloudforensics.start_analysis_vm')
  @mock.patch('turbinia.lib.libcloudforensics.GoogleCloudProject.create_disk_from_snapshot')
  @mock.patch('dftimewolf.lib.collectors.gcloud.GoogleCloudCollector._FindDisksToCopy')
  @mock.patch('turbinia.lib.libcloudforensics.GoogleComputeDisk.snapshot')
  @mock.patch('turbinia.lib.libcloudforensics.GoogleComputeSnapshot.delete')
  @mock.patch('turbinia.lib.libcloudforensics.GoogleComputeInstance.attach_disk')
  def testProcess(self,
                  unused_mock_attach_disk,
                  mock_delete,
                  mock_snapshot,
                  mock_find_disks,
                  mock_create_disk_from_snapshot,
                  mock_start_analysis_vm,
                  mock_add_labels,
                  mock_get_boot_disk):
    """Tests the collector's Process() function."""
    mock_start_analysis_vm.return_value = (FAKE_ANALYSIS_VM, None)
    mock_find_disks.return_value = [
        libcloudforensics.GoogleComputeDisk(
            FAKE_PROJECT,
            'fake_zone',
            'disk1')
    ]
    mock_create_disk_from_snapshot.return_value = FAKE_DISK_COPY
    mock_snapshot.return_value = FAKE_SNAPSHOT
    FAKE_ANALYSIS_VM.add_labels = mock_add_labels
    FAKE_ANALYSIS_VM.get_boot_disk = mock_get_boot_disk
    FAKE_DISK_COPY.add_labels = mock_add_labels

    test_state = state.DFTimewolfState(config.Config)
    gcloud_collector = gcloud.GoogleCloudCollector(test_state)
    gcloud_collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_incident_id',
        'fake_zone',
        42.0,
        16,
        remote_instance_name='my-owned-instance',
    )
    gcloud_collector.Process()

    mock_snapshot.assert_called_once()
    mock_create_disk_from_snapshot.assert_called_with(
        FAKE_SNAPSHOT, disk_name_prefix='incidentfake_incident_id')
    mock_delete.assert_called_once()
    self.assertEqual(test_state.output[0][0], 'fake-analysis-vm')
    self.assertEqual(test_state.output[0][1].name, 'disk1-copy')
    mock_add_labels.assert_has_calls([mock.call({'incident_id': 'fake_incident_id'})])

  # pylint: disable=line-too-long
  @mock.patch('turbinia.lib.libcloudforensics.GoogleComputeBaseResource')
  @mock.patch('turbinia.lib.libcloudforensics.GoogleComputeInstance.get_boot_disk')
  @mock.patch('turbinia.lib.libcloudforensics.GoogleCloudProject.get_disk')
  @mock.patch('turbinia.lib.libcloudforensics.GoogleComputeInstance.list_disks')
  @mock.patch('turbinia.lib.libcloudforensics.GoogleCloudProject.get_instance')
  @mock.patch('turbinia.lib.libcloudforensics.start_analysis_vm')
  # We're manually calling protected functions
  # pylint: disable=protected-access
  def testFindDisksToCopy(self,
                          mock_start_analysis_vm,
                          mock_get_instance,
                          mock_list_disks,
                          mock_get_disk,
                          mock_get_boot_disk,
                          mock_GoogleComputeBaseResource):
    """Tests the FindDisksToCopy function with different SetUp() calls."""
    test_state = state.DFTimewolfState(config.Config)
    gcloud_collector = gcloud.GoogleCloudCollector(test_state)
    mock_start_analysis_vm.return_value = (mock_GoogleComputeBaseResource, None)
    mock_list_disks.return_value = ['bootdisk', 'disk1']
    mock_get_disk.side_effect = ReturnFakeDisk
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_get_boot_disk.return_value = FAKE_BOOT_DISK

    # Nothing is specified, GoogleCloudCollector should collect the instance's
    # boot disk
    gcloud_collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_incident_id',
        'fake_zone',
        42.0,
        16,
        remote_instance_name='my-owned-instance',
    )
    disks = gcloud_collector._FindDisksToCopy()
    self.assertEqual(len(disks), 1)
    self.assertEqual(disks[0].name, 'bootdisk')
    mock_get_boot_disk.assert_called_once()

    # Specifying all_disks should return all disks for the instance
    # (see mock_list_disks return value)
    gcloud_collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_incident_id',
        'fake_zone',
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
