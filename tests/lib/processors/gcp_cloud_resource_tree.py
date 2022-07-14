#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GCP Cloud Tree module."""

import os
import unittest
import json
from datetime import timedelta
import mock

from dftimewolf.lib import state
from dftimewolf.lib.processors import gcp_cloud_resource_tree as gcp_crt
from dftimewolf.lib.processors import gcp_cloud_resource_tree_helper as gcp_crt_helper # pylint: disable=line-too-long

from dftimewolf import config

current_dir = os.path.dirname(os.path.realpath(__file__))


class GCPCloudResourceTreeModuleTest(unittest.TestCase):
  """Tests for the Module class of the GCPCloudResourceTree."""

  def testInitialization(self) -> None:
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    self.assertIsNotNone(processor)

  def testSetup(self) -> None:
    """Tests that the processor is set up correctly."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    processor.SetUp(project_id='test-project-hkhalifa',
                    zone='us-central1-a',
                    resource_name='vm1',
                    resource_id='1809669853321684335',
                    resource_type='gcp_instance',
                    mode='offline')
    self.assertEqual(processor.project_id, 'test-project-hkhalifa')
    self.assertEqual(processor.resource_name, 'vm1')
    self.assertEqual(processor.resource_type, 'gcp_instance')
    self.assertEqual(processor.mode, gcp_crt_helper.OperatingMode.OFFLINE)

  @mock.patch('dftimewolf.lib.processors.gcp_cloud_resource_tree.GCPCloudResourceTree._GetLogMessages') # pylint: disable=line-too-long
  # pylint: disable=invalid-name
  def testGetResourcesMetaDataFromLogs(self, _mock_GetLogMessages) -> None:
    """Tests creation of time ranges for logs query."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    r1 = gcp_crt_helper.Resource()
    r1.creation_timestamp = '2021-09-30 03:00:00'
    r2 = gcp_crt_helper.Resource()
    r2.creation_timestamp = '2021-09-15 01:00:00'
    r3 = gcp_crt_helper.Resource()
    r3.creation_timestamp = '2021-11-01 06:00:00'
    #r1 and r2 are within 30 days
    processor.resources_dict['1'] = r1
    processor.resources_dict['2'] = r2
    #r3 is not within 30 days or r1 or r2
    processor.resources_dict['3'] = r3

    # pylint: disable=protected-access
    processor._GetResourcesMetaDataFromLogs('test-project-hkhalifa')

    _mock_GetLogMessages.assert_has_calls([
        mock.call('test-project-hkhalifa',
                  r2.creation_timestamp - timedelta(hours=1),
                  r1.creation_timestamp + timedelta(hours=1)),
        mock.call('test-project-hkhalifa',
                  r3.creation_timestamp - timedelta(hours=1),
                  r3.creation_timestamp + timedelta(hours=1))
    ],
                                          any_order=True)

  @mock.patch('dftimewolf.lib.processors.gcp_cloud_resource_tree.gcp_common')
  # pylint: disable=invalid-name
  def testRetrieveListOfSnapshots(self, _mock_GCPCommon) -> None:
    """Tests retrieval of project snapshots."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    file_path = os.path.join(current_dir, 'test_data',
                             'compute_api_snapshots_response.jsonl')
    with open(file_path) as json_file:
      response = json.load(json_file)
    _mock_GCPCommon.CreateService().snapshots().list_next.return_value = None
    _mock_GCPCommon.CreateService().snapshots().list().execute.return_value = response     # pylint: disable=line-too-long

    # pylint: disable=protected-access
    result = processor._RetrieveListOfSnapshots('test-project-hkhalifa')

    _mock_GCPCommon.CreateService().snapshots().list.assert_called_with(
        project='test-project-hkhalifa')
    self.assertEqual(len(result), 1)
    sample_snapshot = result.get('9044040911901176879')
    self.assertIsNotNone(sample_snapshot)
    if sample_snapshot:
      self.assertEqual(sample_snapshot.name, 'ds-1')
      self.assertEqual(sample_snapshot.type, 'gce_snapshot')
      self.assertEqual(sample_snapshot.resource_name,'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/global/snapshots/ds-1') # pylint: disable=line-too-long
      self.assertIsNotNone(sample_snapshot.parent)
      if sample_snapshot.parent:
        self.assertEqual(sample_snapshot.parent.id, '220309178143008111')
        self.assertEqual(sample_snapshot.parent.name, 'vm1')
        self.assertEqual(sample_snapshot.parent.type, 'gce_disk')
        self.assertEqual(sample_snapshot.parent.resource_name, 'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/zones/us-central1-a/disks/vm1') # pylint: disable=line-too-long

  @mock.patch('dftimewolf.lib.processors.gcp_cloud_resource_tree.gcp_common')
  # pylint: disable=invalid-name
  def testRetrieveListOfInstanceTemplates(self, _mock_GCPCommon) -> None:
    """Tests retrieval of project instance templates."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    file_path = os.path.join(current_dir, 'test_data',
                             'compute_api_instance_templates_response.jsonl')
    with open(file_path) as json_file:
      response = json.load(json_file)
    _mock_GCPCommon.CreateService().instanceTemplates().list_next.return_value = None # pylint: disable=line-too-long
    _mock_GCPCommon.CreateService().instanceTemplates().list(
    ).execute.return_value = response

    # pylint: disable=protected-access
    result = processor._RetrieveListOfInstanceTemplates(
        'test-project-hkhalifa')

    _mock_GCPCommon.CreateService().instanceTemplates().list.assert_called_with(
        project='test-project-hkhalifa')
    self.assertEqual(len(result), 1)
    sample_instance_template = result.get('8635144168302720856')
    self.assertIsNotNone(sample_instance_template)
    if sample_instance_template:
      self.assertEqual(sample_instance_template.name, 'vm4')
      self.assertEqual(sample_instance_template.type, 'gce_instance_template')
      self.assertEqual(sample_instance_template.resource_name, 'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/global/instanceTemplates/vm4') # pylint: disable=line-too-long
      self.assertIsNotNone(sample_instance_template.parent)
      if sample_instance_template.parent:
        self.assertEqual(sample_instance_template.parent.name, 'vm4')
        self.assertEqual(sample_instance_template.parent.type, 'gce_disk')

  @mock.patch('dftimewolf.lib.processors.gcp_cloud_resource_tree.gcp_common')
  # pylint: disable=invalid-name
  def testRetrieveListOfMachineImages(self, _mock_GCPCommon) -> None:
    """Tests retrieval of project machine images."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    file_path = os.path.join(current_dir, 'test_data',
                             'compute_api_machine_images_response.jsonl')
    with open(file_path) as json_file:
      response = json.load(json_file)
    # pylint: disable=line-too-long
    _mock_GCPCommon.CreateService().machineImages().list_next.return_value = None
    _mock_GCPCommon.CreateService().machineImages().list(
    ).execute.return_value = response

    # pylint: disable=protected-access
    result = processor._RetrieveListOfMachineImages('test-project-hkhalifa')

    _mock_GCPCommon.CreateService().machineImages().list.assert_called_with(
        project='test-project-hkhalifa')
    self.assertEqual(len(result), 1)
    sample_machine_image = result.get('7230903477004199227')
    self.assertIsNotNone(sample_machine_image)
    if sample_machine_image:
      self.assertEqual(sample_machine_image.name, 'vm2')
      self.assertEqual(sample_machine_image.type, 'gce_machine_image')
      self.assertEqual(sample_machine_image.resource_name, 'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/global/machineImages/vm2') # pylint: disable=line-too-long
      self.assertIsNotNone(sample_machine_image.parent)
      if sample_machine_image.parent:
        self.assertEqual(sample_machine_image.parent.name, 'vm1')
        self.assertEqual(sample_machine_image.parent.type, 'gce_instance')
        self.assertEqual(sample_machine_image.parent.resource_name, 'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/zones/us-central1-a/instances/vm1') # pylint: disable=line-too-long

  @mock.patch('dftimewolf.lib.processors.gcp_cloud_resource_tree.gcp_common')
  # pylint: disable=invalid-name
  def testRetrieveListOfDisks(self, _mock_GCPCommon) -> None:
    """Tests retrieval of project disks."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    file_path = os.path.join(current_dir, 'test_data',
                             'compute_api_disks_response.jsonl')
    with open(file_path) as json_file:
      response = json.load(json_file)
    # pylint: disable=line-too-long
    _mock_GCPCommon.CreateService().disks().aggregatedList_next.return_value = None
    _mock_GCPCommon.CreateService().disks().aggregatedList().execute.return_value = response

    # pylint: disable=protected-access
    result = processor._RetrieveListOfDisks('test-project-hkhalifa')

    _mock_GCPCommon.CreateService().disks().aggregatedList.assert_called_with(
        project='test-project-hkhalifa')
    self.assertEqual(len(result), 7)
    sample_disk = result.get('3984203342790800799')
    self.assertIsNotNone(sample_disk)
    if sample_disk:
      self.assertEqual(sample_disk.name, 'dc-1')
      self.assertEqual(sample_disk.type, 'gce_disk')
      self.assertEqual(sample_disk.resource_name, 'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/zones/us-central1-a/disks/dc-1') # pylint: disable=line-too-long
      self.assertIsNotNone(sample_disk.parent)
      if sample_disk.parent:
        self.assertEqual(sample_disk.parent.id, '220309178143008111')
        self.assertEqual(sample_disk.parent.name, 'vm1')
        self.assertEqual(sample_disk.parent.type, 'gce_disk')
        self.assertEqual(sample_disk.parent.resource_name, 'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/zones/us-central1-a/disks/vm1') # pylint: disable=line-too-long

  @mock.patch('dftimewolf.lib.processors.gcp_cloud_resource_tree.gcp_common')
  # pylint: disable=invalid-name
  def testRetrieveListOfDiskImages(self, _mock_GCPCommon) -> None:
    """Tests retrieval of project disk images."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    file_path = os.path.join(current_dir, 'test_data',
                             'compute_api_disk_images_response.jsonl')
    with open(file_path) as json_file:
      response = json.load(json_file)
    _mock_GCPCommon.CreateService().images().list_next.return_value = None
    _mock_GCPCommon.CreateService().images().list().execute.return_value = response # pylint: disable=line-too-long

    # pylint: disable=protected-access
    result = processor._RetrieveListOfDiskImages('test-project-hkhalifa')

    _mock_GCPCommon.CreateService().images().list.assert_called_with(
        project='test-project-hkhalifa')
    self.assertEqual(len(result), 1)
    sample_disk_image = result.get('3532694798424618000')
    self.assertIsNotNone(sample_disk_image)
    if sample_disk_image:
      self.assertEqual(sample_disk_image.name, 'dm-1')
      self.assertEqual(sample_disk_image.type, 'gce_image')
      self.assertEqual(sample_disk_image.resource_name, 'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/global/images/dm-1') # pylint: disable=line-too-long
      self.assertIsNotNone(sample_disk_image.parent)
      if sample_disk_image.parent:
        self.assertEqual(sample_disk_image.parent.id, '8096052277174395644')
        self.assertEqual(sample_disk_image.parent.name, 'vm3')
        self.assertEqual(sample_disk_image.parent.type, 'gce_disk')
        self.assertEqual(sample_disk_image.parent.resource_name, 'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/zones/us-central1-a/disks/vm3') # pylint: disable=line-too-long

  @mock.patch('dftimewolf.lib.processors.gcp_cloud_resource_tree.gcp_common')
  # pylint: disable=invalid-name
  def testRetrieveListOfInstances(self, _mock_GCPCommon) -> None:
    """Tests retrieval of project instances."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    file_path = os.path.join(current_dir, 'test_data',
                             'compute_api_instances_response.jsonl')
    with open(file_path) as json_file:
      response = json.load(json_file)
    # pylint: disable=line-too-long
    _mock_GCPCommon.CreateService().instances().aggregatedList_next.return_value = None
    _mock_GCPCommon.CreateService().instances().aggregatedList().execute.return_value = response

    # pylint: disable=protected-access
    result = processor._RetrieveListOfInstances('test-project-hkhalifa')

    _mock_GCPCommon.CreateService().instances().aggregatedList.assert_called_with(
        project='test-project-hkhalifa')
    self.assertEqual(len(result), 7)
    sample_instance = result.get('1809669853321684335')
    self.assertIsNotNone(sample_instance)
    if sample_instance:
      self.assertEqual(sample_instance.name, 'vm1')
      self.assertEqual(sample_instance.type, 'gce_instance')
      self.assertEqual(sample_instance.resource_name, 'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/zones/us-central1-a/instances/vm1') # pylint: disable=line-too-long
      self.assertIsNotNone(sample_instance.parent)
      if sample_instance.parent:
        self.assertEqual(sample_instance.parent.name, 'vm1')
        self.assertEqual(sample_instance.parent.type, 'gce_disk')
        self.assertEqual(sample_instance.parent.resource_name, 'https://www.googleapis.com/compute/beta/projects/test-project-hkhalifa/zones/us-central1-a/disks/vm1') # pylint: disable=line-too-long


  @mock.patch.object(gcp_crt.GCPCloudResourceTree, "_SearchForDeletedResource")
  # pylint: disable=invalid-name
  def testGetResourceParentTree(self, _mock_SearchForDeletedResource) -> None:
    """Tests retrieval of resource parent tree."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    file_path = os.path.join(current_dir, 'test_data',
                             'gcp-project-logs.jsonl')
    _mock_SearchForDeletedResource.return_value = None
    log_messages = []
    with open(file_path) as log_file:
      for line in log_file:
        log_messages.append(json.loads(line))
    # pylint: disable=protected-access
    processor._ParseLogMessages(log_messages)

    # pylint: disable=line-too-long
    parent_resource_of_vm1 = processor._GetResourceParentTree(processor.resources_dict['1809669853321684335'])

    self.assertIsNotNone(parent_resource_of_vm1)
    if parent_resource_of_vm1:
      self.assertEqual(parent_resource_of_vm1.name, 'vm1')
      self.assertEqual(parent_resource_of_vm1.type, 'gce_disk')
      self.assertEqual(parent_resource_of_vm1.resource_name, 'projects/test-project-hkhalifa/zones/us-central1-a/disks/vm1')
      self.assertIsNotNone(parent_resource_of_vm1.parent)
      if parent_resource_of_vm1.parent:
        self.assertEqual(parent_resource_of_vm1.parent.name, 'debian-10-buster-v20210916')
        self.assertEqual(parent_resource_of_vm1.parent.type, 'gce_image')
        self.assertEqual(parent_resource_of_vm1.parent.resource_name, 'projects/debian-cloud/global/images/debian-10-buster-v20210916')
        self.assertIsNone(parent_resource_of_vm1.parent.parent)
      # check if resource is in children
      self.assertEqual(len(parent_resource_of_vm1.children), 1)
      self.assertIn(processor.resources_dict['1809669853321684335'], parent_resource_of_vm1.children)

    # Test if deleted resource is detected while building parent tree
    parent_resource_of_vm10 = processor._GetResourceParentTree(processor.resources_dict['963895663494893499']) # pylint: disable=line-too-long
    self.assertIsNotNone(parent_resource_of_vm10)
    _mock_SearchForDeletedResource.assert_called()

  def testParseLogMessages(self) -> None:
    """Tests parse log messages."""
    test_state = state.DFTimewolfState(config.Config)
    processor = gcp_crt.GCPCloudResourceTree(test_state)
    file_path_resources_dict = os.path.join(current_dir, 'test_data',
                             'resources_dict_dump.jsonl')
    with open(file_path_resources_dict) as resources_dict_file:
      stored_resources_dict = json.loads(resources_dict_file.read())

    file_path_logs = os.path.join(current_dir, 'test_data',
                             'gcp-project-logs.jsonl')
    log_messages = []
    with open(file_path_logs) as log_file:
      for line in log_file:
        log_messages.append(json.loads(line))

    # pylint: disable=protected-access
    processor._ParseLogMessages(log_messages)

    current_resources_dict = json.dumps(processor.resources_dict, cls=gcp_crt_helper.ResourceEncoder) # pylint: disable=line-too-long
    current_resources_dict = json.loads(current_resources_dict)
    self.assertEqual(len(processor.resources_dict), 32)
    self.assertEqual(stored_resources_dict, current_resources_dict)
