#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Turbinia processor."""

import os
import unittest
import mock
import six

from libcloudforensics.providers.gcp.internal.compute import GoogleComputeDisk
from dftimewolf.lib import state
from dftimewolf.lib import errors

# The easiest way to load our test Turbinia config is to add an environment
# variable
current_dir = os.path.dirname(os.path.realpath(__file__))
os.environ['TURBINIA_CONFIG_PATH'] = os.path.join(current_dir, 'test_data')
# pylint: disable=wrong-import-position
from dftimewolf.lib.containers import containers
from dftimewolf.lib.processors import turbinia_gcp

from dftimewolf import config

# Manually set TURBINIA_PROJECT to the value we expect.
# pylint: disable=wrong-import-position, wrong-import-order
from turbinia import config as turbinia_config
from turbinia.message import TurbiniaRequest

turbinia_config.TURBINIA_PROJECT = 'turbinia-project'

YARA_RULE = """rule dummy { condition: false }"""


class TurbiniaGCPProcessorTest(unittest.TestCase):
  """Tests for the Turbinia processor."""

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia_gcp.TurbiniaGCPProcessor(test_state)
    self.assertIsNotNone(turbinia_processor)

  @mock.patch('turbinia.client.get_turbinia_client')
  # pylint: disable=invalid-name
  def testSetup(self, _mock_TurbiniaClient):
    """Tests that the processor is set up correctly."""
    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia_gcp.TurbiniaGCPProcessor(test_state)
    turbinia_processor.SetUp(
        turbinia_config_file=None,
        disk_names='disk-1',
        project='turbinia-project',
        turbinia_recipe=None,
        turbinia_zone='europe-west1',
        sketch_id=123)
    turbinia_processor.client.create_request.return_value = TurbiniaRequest()
    self.assertEqual(turbinia_processor.project, 'turbinia-project')
    self.assertEqual(turbinia_processor.turbinia_zone, 'europe-west1')
    self.assertEqual(turbinia_processor.turbinia_recipe, None)
    self.assertEqual(turbinia_processor.sketch_id, 123)
    self.assertEqual(test_state.errors, [])
    self.assertEqual(
        'disk-1',
        test_state.GetContainers(
            turbinia_processor.GetThreadOnContainerType())[0].name)

    # TURBINIA_REGION is dynamically generated
    # pylint: disable=no-member
    self.assertEqual(
        turbinia_processor.turbinia_region,
        turbinia_gcp.turbinia_config.TURBINIA_REGION)
    # pylint: disable=protected-access
    six.assertRegex(
        self, turbinia_processor._output_path, '(/tmp/tmp|/var/folders).+')

  @mock.patch('turbinia.client.get_turbinia_client')
  # pylint: disable=invalid-name
  def testWrongProject(self, _mock_TurbiniaClient):
    """Tests that specifying the wrong Turbinia project generates an error."""
    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia_gcp.TurbiniaGCPProcessor(test_state)
    with self.assertRaises(errors.DFTimewolfError) as error:
      turbinia_processor.SetUp(
          turbinia_config_file=None,
          disk_names='disk-1',
          project='turbinia-wrong-project',
          turbinia_recipe=None,
          turbinia_zone='europe-west1',
          sketch_id=None)
      turbinia_processor.client.create_request.return_value = TurbiniaRequest()
    self.assertEqual(len(test_state.errors), 1)
    self.assertEqual(test_state.errors[0], error.exception)
    error_msg = error.exception.message
    self.assertEqual(
        error_msg, 'Specified project turbinia-wrong-project does '
        'not match Turbinia configured project '
        'turbinia-project. Use '
        'gcp_turbinia_disk_copy_ts recipe to copy the '
        'disk into the same project.')
    self.assertTrue(error.exception.critical)

  @mock.patch('dftimewolf.lib.processors.turbinia_base.turbinia_config')
  @mock.patch('turbinia.client.get_turbinia_client')
  # pylint: disable=invalid-name
  def testWrongSetup(self, _mock_TurbiniaClient, mock_turbinia_config):
    """Tests that invalid setup options generate errors."""
    params = [{
        'turbinia_config_file': None,
        'disk_names': 'disk-1',
        'project': None,
        'turbinia_recipe': None,
        'turbinia_zone': 'europe-west1',
        'sketch_id': None,
    }, {
        'turbinia_config_file': None,
        'disk_names': 'disk-1',
        'project': 'turbinia-project',
        'turbinia_recipe': None,
        'turbinia_zone': None,
        'sketch_id': None,
    }]
    expected_error = (
        'project or turbinia_zone are not all '
        'specified, bailing out')

    for combination in params:
      mock_turbinia_config.TURBINIA_PROJECT = combination['project']
      mock_turbinia_config.TURBINIA_ZONE = combination['turbinia_zone']
      test_state = state.DFTimewolfState(config.Config)
      turbinia_processor = turbinia_gcp.TurbiniaGCPProcessor(test_state)
      with self.assertRaises(errors.DFTimewolfError) as error:
        turbinia_processor.SetUp(**combination)

      self.assertEqual(len(test_state.errors), 1)
      self.assertEqual(test_state.errors[0], error.exception)
      error_msg = error.exception.message
      self.assertEqual(error_msg, expected_error)
      self.assertTrue(error.exception.critical)

  @mock.patch('os.path.exists')
  @mock.patch('turbinia.output_manager.GCSOutputWriter')
  @mock.patch('turbinia.evidence.GoogleCloudDisk')
  @mock.patch('turbinia.client.get_turbinia_client')
  # pylint: disable=invalid-name
  def testProcessFromParams(
      self, _mock_TurbiniaClient, mock_GoogleCloudDisk, mock_GCSOutputWriter,
      mock_exists):
    """Tests that the processor processes data correctly when a disk name is
    passed in as a parameter."""

    test_state = state.DFTimewolfState(config.Config)
    test_state.StoreContainer(
        containers.YaraRule(
            name='dummy_yara', rule_text="rule dummy { condition: false }"))
    turbinia_processor = turbinia_gcp.TurbiniaGCPProcessor(test_state)
    turbinia_processor.SetUp(
        turbinia_config_file=None,
        disk_names='disk-1',
        project='turbinia-project',
        turbinia_recipe=None,
        turbinia_zone='europe-west1',
        sketch_id=4567)

    recipe = {
        'globals': {
            'sketch_id':
                4567,
            'yara_rules':
                YARA_RULE,
            'jobs_denylist': [
                'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob',
                'PhotorecJob'
            ]
        }
    }

    turbinia_processor.client.create_request.return_value = TurbiniaRequest(
        recipe=recipe)
    turbinia_processor.client.get_task_data.return_value = [{
        'saved_paths': [
            '/fake/data.plaso',
            '/fake/data2.plaso',
            '/another/random/file.txt',
            'gs://BinaryExtractorTask.tar.gz',
        ]
    }]

    # Return true so the tests assumes the above file exists
    mock_exists.return_value = True

    # Our GS path will be downloaded to this fake local path
    local_mock = mock.MagicMock()
    local_mock.copy_from.return_value = '/local/BinaryExtractorTask.tar.gz'
    mock_GCSOutputWriter.return_value = local_mock

    turbinia_processor.PreProcess()
    in_containers = test_state.GetContainers(
        turbinia_processor.GetThreadOnContainerType())
    for c in in_containers:
      turbinia_processor.Process(c)
    turbinia_processor.PostProcess()

    mock_GoogleCloudDisk.assert_called_with(
        disk_name='disk-1', project='turbinia-project', zone='europe-west1')

    # These are mock classes, so there is a member
    # pylint: disable=no-member
    turbinia_processor.client.send_request.assert_called()
    request = turbinia_processor.client.send_request.call_args[0][0]
    self.assertEqual(request.recipe['globals']['sketch_id'], 4567)
    self.assertListEqual(
        request.recipe['globals']['jobs_denylist'],
        ['StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob', 'PhotorecJob'])
    turbinia_processor.client.get_task_data.assert_called()
    self.assertEqual(
        request.recipe['globals']['yara_rules'],
        "rule dummy { condition: false }")

    # pylint: disable=protected-access
    mock_GCSOutputWriter.assert_any_call(
        'gs://BinaryExtractorTask.tar.gz',
        local_output_dir=turbinia_processor._output_path)
    self.assertEqual(test_state.errors, [])
    ti_containers = test_state.GetContainers(containers.ThreatIntelligence)
    file_containers = test_state.GetContainers(containers.File)

    # Make sure that file.txt is ignored
    self.assertEqual(len(file_containers), 2)

    self.assertEqual(ti_containers[0].name, 'BinaryExtractorResults')
    self.assertEqual(ti_containers[0].path, '/local/BinaryExtractorTask.tar.gz')

    self.assertEqual(file_containers[0].name, 'turbinia-project-disk-1')
    self.assertEqual(file_containers[1].name, 'turbinia-project-disk-1')
    self.assertEqual(file_containers[0].path, '/fake/data.plaso')
    self.assertEqual(file_containers[1].path, '/fake/data2.plaso')

  @mock.patch('os.path.exists')
  @mock.patch('turbinia.output_manager.GCSOutputWriter')
  @mock.patch('turbinia.evidence.GoogleCloudDisk')
  @mock.patch('turbinia.client.get_turbinia_client')
  # pylint: disable=invalid-name
  def testProcessFromState(
      self, _mock_TurbiniaClient, mock_GoogleCloudDisk, mock_GCSOutputWriter,
      mock_exists):
    """Tests that the processor processes data correctly when a GCEDisk is
    received from the state.
    """
    test_state = state.DFTimewolfState(config.Config)
    test_state.StoreContainer(
      containers.YaraRule(
        name='dummy_yara', rule_text="rule dummy { condition: false }")
    )
    test_state.StoreContainer(containers.GCEDiskEvidence(
        name='disk-1', project='turbinia-project'))
    turbinia_processor = turbinia_gcp.TurbiniaGCPProcessor(test_state)
    turbinia_processor.SetUp(
        turbinia_config_file=None,
        project='turbinia-project',
        turbinia_recipe=None,
        turbinia_zone='europe-west1',
        sketch_id=4567)

    recipe = {
        'globals': {
            'sketch_id':
                4567,
            'yara_rules':
                YARA_RULE,
            'jobs_denylist': [
                'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob',
                'PhotorecJob'
            ]
        }
    }
    turbinia_processor.client.create_request.return_value = TurbiniaRequest(
        recipe=recipe)
    turbinia_processor.client.get_task_data.return_value = [{
        'saved_paths': [
            '/fake/data.plaso',
            '/fake/data2.plaso',
            '/another/random/file.txt',
            'gs://BinaryExtractorTask.tar.gz',
        ]
    }]

    # Return true so the tests assumes the above file exists
    mock_exists.return_value = True

    # Our GS path will be downloaded to this fake local path
    local_mock = mock.MagicMock()
    local_mock.copy_from.return_value = '/local/BinaryExtractorTask.tar.gz'
    mock_GCSOutputWriter.return_value = local_mock

    turbinia_processor.PreProcess()
    in_containers = test_state.GetContainers(
        turbinia_processor.GetThreadOnContainerType())
    for c in in_containers:
      turbinia_processor.Process(c)
    turbinia_processor.PostProcess()

    mock_GoogleCloudDisk.assert_called_with(
        disk_name='disk-1', project='turbinia-project', zone='europe-west1')

    # These are mock classes, so there is a member
    # pylint: disable=no-member
    turbinia_processor.client.send_request.assert_called()
    request = turbinia_processor.client.send_request.call_args[0][0]
    self.assertEqual(request.recipe['globals']['sketch_id'], 4567)
    self.assertListEqual(
        request.recipe['globals']['jobs_denylist'],
        ['StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob', 'PhotorecJob'])
    turbinia_processor.client.get_task_data.assert_called()
    self.assertEqual(
        request.recipe['globals']['yara_rules'],
        "rule dummy { condition: false }")

    # pylint: disable=protected-access
    mock_GCSOutputWriter.assert_any_call(
        'gs://BinaryExtractorTask.tar.gz',
        local_output_dir=turbinia_processor._output_path)
    self.assertEqual(test_state.errors, [])
    ti_containers = test_state.GetContainers(containers.ThreatIntelligence)
    file_containers = test_state.GetContainers(containers.File)

    # Make sure that file.txt is ignored
    self.assertEqual(len(file_containers), 2)

    self.assertEqual(ti_containers[0].name, 'BinaryExtractorResults')
    self.assertEqual(ti_containers[0].path, '/local/BinaryExtractorTask.tar.gz')

    self.assertEqual(file_containers[0].name, 'turbinia-project-disk-1')
    self.assertEqual(file_containers[1].name, 'turbinia-project-disk-1')
    self.assertEqual(file_containers[0].path, '/fake/data.plaso')
    self.assertEqual(file_containers[1].path, '/fake/data2.plaso')

  @mock.patch('turbinia.evidence.GoogleCloudDisk')
  @mock.patch('turbinia.client.get_turbinia_client')
  # pylint: disable=invalid-name
  def testProcessCrossProject(self,
                              _mock_TurbiniaClient,
                              mock_GoogleCloudDisk):
    """Tests that process does nothing if the disks are in another project."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.StoreContainer(containers.GCEDiskEvidence(
        name='disk-1', project='another-project'))
    turbinia_processor = turbinia_gcp.TurbiniaGCPProcessor(test_state)
    turbinia_processor.SetUp(
        turbinia_config_file=None,
        project='turbinia-project',
        turbinia_zone='europe-west1',
        turbinia_recipe=None,
        sketch_id=4567)

    turbinia_processor.PreProcess()
    in_containers = test_state.GetContainers(
        turbinia_processor.GetThreadOnContainerType())
    for c in in_containers:
      turbinia_processor.Process(c)
    turbinia_processor.PostProcess()

    file_containers = test_state.GetContainers(containers.File)
    self.assertEqual(len(file_containers), 0)

    # pylint: disable=no-member
    mock_GoogleCloudDisk.assert_not_called()
    turbinia_processor.client.send_request.assert_not_called()

  @mock.patch('turbinia.output_manager.GCSOutputWriter')
  # pylint: disable=invalid-name
  def testDownloadFilesFromGCS(self, mock_GCSOutputWriter):
    """Tests _DownloadFilesFromGCS"""

    def _fake_copy(filename):
      return '/fake/local/' + filename.rsplit('/')[-1]

    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia_gcp.TurbiniaGCPProcessor(test_state)
    mock_GCSOutputWriter.return_value.copy_from = _fake_copy
    fake_paths = ['gs://hashes.json', 'gs://results.plaso']
    # pylint: disable=protected-access
    local_paths = turbinia_processor._DownloadFilesFromGCS('fake', fake_paths)
    self.assertEqual(
        local_paths, [('fake', '/fake/local/hashes.json'),
                      ('fake', '/fake/local/results.plaso')])

  def testDeterminePaths(self):
    """Tests _DeterminePaths"""
    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia_gcp.TurbiniaGCPProcessor(test_state)
    fake_task_data = [{
        'saved_paths': ['/local/path.plaso', '/ignoreme/'],
    }, {
        'saved_paths': ['gs://hashes.json', '/tmp/BinaryExtractorTask.tar.gz'],
    }]
    # pylint: disable=protected-access
    local_paths, gs_paths = turbinia_processor._DeterminePaths(fake_task_data)
    self.assertEqual(
        local_paths, ['/local/path.plaso', '/tmp/BinaryExtractorTask.tar.gz'])
    self.assertEqual(gs_paths, ['gs://hashes.json'])

  @mock.patch('turbinia.client.get_turbinia_client')
  # pylint: disable=invalid-name
  def testPreProcess(self, _mockTurbiniaClient):
    """Tests that ForensicsVM containers are picked up properly.

    We store a ForensicsVM container in the state, run PreProcess, then check
    that the state contains a GCEDisk as expected."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.StoreContainer(
        containers.ForensicsVM(
            name='ForensicsVM',
            evidence_disk=GoogleComputeDisk(
                name='disk-1',
                project_id='turbinia-project',
                zone='europe-west1'),
            platform='gcp'))

    turbinia_processor = turbinia_gcp.TurbiniaGCPProcessor(test_state)
    turbinia_processor.SetUp(
        turbinia_config_file=None,
        project='turbinia-project',
        turbinia_recipe=None,
        turbinia_zone='europe-west1',
        sketch_id=4567)
    turbinia_processor.client.create_request.return_value = TurbiniaRequest()
    turbinia_processor.PreProcess()

    out_containers = test_state.GetContainers(containers.GCEDiskEvidence)

    self.assertEqual(len(out_containers), 1)
    self.assertEqual(out_containers[0].name, 'disk-1')


if __name__ == '__main__':
  unittest.main()
