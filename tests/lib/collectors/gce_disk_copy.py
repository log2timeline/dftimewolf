#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the GCEDiskCopy collector."""

import unittest

from googleapiclient.errors import HttpError
import httplib2

import mock
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute
from libcloudforensics import errors as lcf_errors

from dftimewolf import config
from dftimewolf.lib import errors, state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.collectors import gce_disk_copy

FAKE_PROJECT = gcp_project.GoogleCloudProject(
    'test-target-project-name',
    'fake_zone')
FAKE_INSTANCE = compute.GoogleComputeInstance(
    FAKE_PROJECT.project_id,
    'fake_zone',
    'fake-instance')
FAKE_DISK = compute.GoogleComputeDisk(
    FAKE_PROJECT.project_id,
    'fake_zone',
    'disk1')
FAKE_DISK_MULTIPLE = [
    compute.GoogleComputeDisk(
        FAKE_PROJECT.project_id,
        'fake_zone',
        'disk1'),
    compute.GoogleComputeDisk(
        FAKE_PROJECT.project_id,
        'fake_zone',
        'disk2')
]
FAKE_BOOT_DISK = compute.GoogleComputeDisk(
    FAKE_PROJECT.project_id,
    'fake_zone',
    'bootdisk')
FAKE_DISK_COPY = [
    compute.GoogleComputeDisk(
        FAKE_PROJECT.project_id,
        'fake_zone',
        'disk1-copy'),
    compute.GoogleComputeDisk(
        FAKE_PROJECT.project_id,
        'fake_zone',
        'disk2-copy')
]

class GCEDiskCopyTest(unittest.TestCase):
  """Tests for the GCEDiskCopy collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    self.assertIsNotNone(collector)

  def testSetUp(self):
    """Tests the SetUp method of the collector."""
    test_state = state.DFTimewolfState(config.Config)

    # Test setup with single disk and instance
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        'test-destination-project-name',
        'test-source-project-name',
        'fake_zone',
        remote_instance_names='my-owned-instance',
        disk_names='fake-disk',
        all_disks=True,
        stop_instances=True
    )
    self.assertEqual(test_state.errors, [])
    self.assertEqual(collector.destination_project.project_id,
                     'test-destination-project-name')
    self.assertEqual(collector.source_project.project_id,
                     'test-source-project-name')
    self.assertEqual(collector.remote_instance_names, ['my-owned-instance'])
    self.assertEqual(collector.disk_names, ['fake-disk'])
    self.assertEqual(collector.all_disks, True)
    self.assertEqual(collector.stop_instances, True)

    # Test setup with multiple disks and instances
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        'test-destination-project-name',
        'test-source-project-name',
        'fake_zone',
        'my-owned-instance1,my-owned-instance2',
        'fake-disk-1,fake-disk-2',
        False,
        False
    )
    self.assertEqual(test_state.errors, [])
    self.assertEqual(collector.destination_project.project_id,
                     'test-destination-project-name')
    self.assertEqual(collector.source_project.project_id,
                     'test-source-project-name')
    self.assertEqual(sorted(collector.remote_instance_names), sorted([
                     'my-owned-instance1', 'my-owned-instance2']))
    self.assertEqual(sorted(collector.disk_names), sorted([
                     'fake-disk-1', 'fake-disk-2']))
    self.assertEqual(collector.all_disks, False)
    self.assertEqual(collector.stop_instances, False)

    # Test setup with no destination project
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        None,
        'test-source-project-name',
        'fake_zone',
        remote_instance_names='my-owned-instance',
        disk_names='fake-disk',
        all_disks=True,
        stop_instances=True
    )
    self.assertEqual(test_state.errors, [])
    self.assertEqual(collector.destination_project.project_id,
                     'test-source-project-name')
    self.assertEqual(collector.source_project.project_id,
                     'test-source-project-name')
    self.assertEqual(collector.remote_instance_names, ['my-owned-instance'])
    self.assertEqual(collector.disk_names, ['fake-disk'])
    self.assertEqual(collector.all_disks, True)
    self.assertEqual(collector.stop_instances, True)

  def testSetUpNothingProvided(self):
    """Tests that SetUp fails if no disks or instances are provided."""
    test_state = state.DFTimewolfState(config.Config)
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    with self.assertRaises(errors.DFTimewolfError) as error:
      collector.SetUp(
          'test-destination-project-name',
          'test-source-project-name',
          'fake_zone',
          None,
          None,
          False,
          False
      )
    self.assertEqual(error.exception.message,
        'You need to specify at least an instance name or disks to copy')

  def testStopWithNoInstance(self):
    """Tests that SetUp fails if stop instance is requested, but no instance
    provided.
    """
    test_state = state.DFTimewolfState(config.Config)
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    with self.assertRaises(errors.DFTimewolfError) as error:
      collector.SetUp(
          'test-destination-project-name',
          'test-source-project-name',
          'fake_zone',
          None,
          'disk1',
          False,
          True
      )
    self.assertEqual(error.exception.message,
        'You need to specify an instance name to stop the instance')

  # pylint: disable=line-too-long,invalid-name
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.GetBootDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetDisk')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.ListDisks')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetInstance')
  # We're manually calling protected functions
  # pylint: disable=protected-access
  def testPreProcess(self,
                     mock_get_instance,
                     mock_list_disks,
                     mock_get_disk,
                     mock_GetBootDisk):
    """Tests the _FindDisksToCopy function with different SetUp() calls."""
    test_state = state.DFTimewolfState(config.Config)
    mock_list_disks.return_value = {
        'bootdisk': FAKE_BOOT_DISK,
        'disk1': FAKE_DISK
    }
    mock_get_disk.return_value = FAKE_DISK
    mock_get_instance.return_value = FAKE_INSTANCE
    mock_GetBootDisk.return_value = FAKE_BOOT_DISK

    # Nothing is specified, GoogleCloudCollector should collect the instance's
    # boot disk
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_zone',
        'my-owned-instance',
        None,
        False,
        False
    )
    collector.PreProcess()
    disks = test_state.GetContainers(containers.GCEDisk)
    self.assertEqual(len(disks), 1)
    self.assertEqual(disks[0].name, 'bootdisk')
    mock_GetBootDisk.assert_called_once()

    # Specifying all_disks should return all disks for the instance
    # (see mock_list_disks return value)
    test_state.GetContainers(containers.GCEDisk, True)  # Clear containers first
    collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_zone',
        'my-owned-instance',
        None,
        True,
        False
    )
    collector.PreProcess()
    disks = test_state.GetContainers(containers.GCEDisk)
    self.assertEqual(len(disks), 2)
    self.assertEqual(disks[0].name, 'bootdisk')
    self.assertEqual(disks[1].name, 'disk1')

    # Specifying a csv list of disks should have those included also
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    test_state.GetContainers(containers.GCEDisk, True)  # Clear containers first
    collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_zone',
        'my-owned-instance',
        'another_disk_1,another_disk_2',
        True,
        False
    )
    collector.PreProcess()
    disks = test_state.GetContainers(containers.GCEDisk)
    self.assertEqual(len(disks), 4)
    self.assertEqual(disks[0].name, 'another_disk_1')
    self.assertEqual(disks[1].name, 'another_disk_2')
    self.assertEqual(disks[2].name, 'bootdisk')
    self.assertEqual(disks[3].name, 'disk1')

  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetInstance')
  def testInstanceNotFound(self, mock_GetInstance):
    """Test that an error is thrown when the instance isn't found."""
    mock_GetInstance.side_effect = lcf_errors.ResourceNotFoundError('message',
                                                                    'name')

    test_state = state.DFTimewolfState(config.Config)
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_zone',
        'nonexistent',
        None,
        False,
        False
    )
    with self.assertRaises(errors.DFTimewolfError) as error:
      collector.PreProcess()

    self.assertEqual(error.exception.message,
        'Instance "nonexistent" in test-target-project-name not found or '
        'insufficient permissions')

  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetInstance')
  def testHTTPErrors(self, mock_GetInstance):
    """Tests the 403 checked for in PreProcess."""
    test_state = state.DFTimewolfState(config.Config)

    # 403
    mock_GetInstance.side_effect = HttpError(httplib2.Response({
        'status': 403,
        'reason': 'The caller does not have permission'
    }), b'')

    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_zone',
        'nonexistent',
        None,
        False,
        False
    )
    with self.assertRaises(errors.DFTimewolfError) as error:
      collector.PreProcess()
    self.assertEqual(error.exception.message,
        '403 response. Do you have appropriate permissions on the project?')

    # Other (500)
    mock_GetInstance.side_effect = HttpError(httplib2.Response({
        'status': 500,
        'reason': 'Internal Server Error'
    }), b'')

    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_zone',
        'nonexistent',
        None,
        False,
        False
    )
    with self.assertRaises(errors.DFTimewolfError) as error:
      collector.PreProcess()
    self.assertEqual(error.exception.message,
        '<HttpError 500 "Ok">')

  # pylint: disable=line-too-long
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleCloudCompute.GetInstance')
  @mock.patch('libcloudforensics.providers.gcp.forensics.CreateDiskCopy')
  @mock.patch('dftimewolf.lib.collectors.gce_disk_copy.GCEDiskCopy._GetDisksFromInstance')
  @mock.patch('libcloudforensics.providers.gcp.internal.compute.GoogleComputeInstance.ListDisks')
  def testProcess(self,
                  mock_list_disks,
                  mock_getDisksFromInstance,
                  mock_CreateDiskCopy,
                  mock_GetInstance):
    """Tests the collector's Process() function."""
    mock_getDisksFromInstance.return_value = FAKE_DISK_MULTIPLE
    mock_CreateDiskCopy.side_effect = FAKE_DISK_COPY
    mock_GetInstance.return_value = FAKE_INSTANCE
    mock_list_disks.return_value = {
        'bootdisk': FAKE_BOOT_DISK,
        'disk1': FAKE_DISK
    }

    test_state = state.DFTimewolfState(config.Config)
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_zone',
        'my-owned-instance',
        None,
        True,
        True
    )
    FAKE_INSTANCE.Stop = mock.MagicMock()

    collector.PreProcess()
    conts = test_state.GetContainers(collector.GetThreadOnContainerType())
    for d in conts:
      collector.Process(d)  # pytype: disable=wrong-arg-types
      mock_CreateDiskCopy.assert_called_with(
          'test-target-project-name',
          'test-analysis-project-name',
          FAKE_INSTANCE.zone,
          disk_name=d.name)  # pytype: disable=attribute-error
    collector.PostProcess()

    FAKE_INSTANCE.Stop.assert_called_once()

    out_disks = test_state.GetContainers(containers.GCEDiskEvidence)
    out_disk_names = sorted([d.name for d in out_disks])
    expected_disk_names = ['disk1-copy', 'disk2-copy']
    self.assertEqual(out_disk_names, expected_disk_names)
    for d in out_disks:
      self.assertEqual(d.project, 'test-analysis-project-name')

    # Do it again, but we don't want to stop the instance this time.
    # First, clear the containers
    test_state.GetContainers(containers.GCEDisk, True)
    test_state.GetContainers(containers.GCEDiskEvidence, True)
    mock_CreateDiskCopy.side_effect = FAKE_DISK_COPY
    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        'test-analysis-project-name',
        'test-target-project-name',
        'fake_zone',
        'my-owned-instance',
        None,
        True,
        False,
    )
    FAKE_INSTANCE.Stop = mock.MagicMock()

    collector.PreProcess()
    conts = test_state.GetContainers(collector.GetThreadOnContainerType())
    for d in conts:
      collector.Process(d)  # pytype: disable=wrong-arg-types
      mock_CreateDiskCopy.assert_called_with(
          'test-target-project-name',
          'test-analysis-project-name',
          FAKE_INSTANCE.zone,
          disk_name=d.name)  # pytype: disable=attribute-error
    collector.PostProcess()

    FAKE_INSTANCE.Stop.assert_not_called()
    out_disks = test_state.GetContainers(containers.GCEDiskEvidence)
    out_disk_names = sorted([d.name for d in out_disks])
    expected_disk_names = ['disk1-copy', 'disk2-copy']
    self.assertEqual(out_disk_names, expected_disk_names)
    for d in out_disks:
      self.assertEqual(d.project, 'test-analysis-project-name')

  @mock.patch('libcloudforensics.providers.gcp.forensics.CreateDiskCopy')
  def testProcessDiskCopyErrors(self, mock_CreateDiskCopy):
    """Tests that Process errors correctly in some scenarios."""
    test_state = state.DFTimewolfState(config.Config)

    # Fail if the disk cannot be found.
    mock_CreateDiskCopy.side_effect = lcf_errors.ResourceNotFoundError(
        'Could not find disk "nonexistent": Disk nonexistent was not found in '
        'project test-source-project-name',
        'name')

    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        'test-destination-project-name',
        'test-source-project-name',
        'fake_zone',
        None,
        'nonexistent',
        False,
        False
    )
    collector.PreProcess()
    conts = test_state.GetContainers(collector.GetThreadOnContainerType())
    for d in conts:
      collector.Process(d)  # pytype: disable=wrong-arg-types
    with self.assertRaises(errors.DFTimewolfError) as error:
      collector.PostProcess()
    self.assertEqual(error.exception.message,
        'No successful disk copy operations completed.')

    # Fail if the disk cannot be created
    mock_CreateDiskCopy.side_effect = lcf_errors.ResourceCreationError(
        'Could not create disk. Permission denied.',
        'name')

    collector = gce_disk_copy.GCEDiskCopy(test_state)
    collector.SetUp(
        'test-destination-project-name',
        'test-source-project-name',
        'fake_zone',
        None,
        'nonexistent',
        False,
        False
    )
    collector.PreProcess()
    conts = test_state.GetContainers(collector.GetThreadOnContainerType())
    with self.assertRaises(errors.DFTimewolfError) as error:
      for d in conts:
        collector.Process(d)  # pytype: disable=wrong-arg-types
    self.assertEqual(error.exception.message,
        'Could not create disk. Permission denied.')

if __name__ == '__main__':
  unittest.main()
