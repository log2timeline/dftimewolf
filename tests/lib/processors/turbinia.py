#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Turbinia processor."""

from __future__ import unicode_literals

import os
import unittest
import mock
import six

from dftimewolf.lib import state

# The easiest way to load our test Turbinia config is to add an environment
# variable
current_dir = os.path.dirname(os.path.realpath(__file__))
os.environ['TURBINIA_CONFIG_PATH'] = os.path.join(current_dir, 'test_data')
# pylint: disable=wrong-import-position
from dftimewolf.lib.processors import turbinia

from dftimewolf import config


class TurbiniaProcessorTest(unittest.TestCase):
  """Tests for the Turbinia processor."""

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia.TurbiniaProcessor(test_state)
    self.assertIsNotNone(turbinia_processor)

  @mock.patch('turbinia.client.TurbiniaClient')
  # pylint: disable=invalid-name
  def testSetup(self, _mock_TurbiniaClient):
    """Tests that the processor is set up correctly."""
    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia.TurbiniaProcessor(test_state)
    turbinia_processor.setup(
        disk_name='disk-1',
        project='turbinia-project',
        turbinia_zone='europe-west1')
    self.assertEqual(turbinia_processor.disk_name, 'disk-1')
    self.assertEqual(turbinia_processor.project, 'turbinia-project')
    self.assertEqual(turbinia_processor.turbinia_zone, 'europe-west1')
    self.assertEqual(test_state.errors, [])

    # TURBINIA_REGION is dynamically generated
    # pylint: disable=no-member
    self.assertEqual(turbinia_processor.turbinia_region,
                     turbinia.turbinia_config.TURBINIA_REGION)
    # pylint: disable=protected-access
    six.assertRegex(self, turbinia_processor._output_path,
                    '(/tmp/tmp|/var/folders).+')

  @mock.patch('turbinia.client.TurbiniaClient')
  # pylint: disable=invalid-name
  def testWrongProject(self, _mock_TurbiniaClient):
    """Tests that specifying the wrong Turbinia project generates an error."""
    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia.TurbiniaProcessor(test_state)
    turbinia_processor.setup(
        disk_name='disk-1',
        project='turbinia-wrong-project',
        turbinia_zone='europe-west1')

    self.assertEqual(len(test_state.errors), 1)
    error_msg, is_critical = test_state.errors[0]
    self.assertEqual(error_msg, 'Specified project turbinia-wrong-project does'
                                ' not match Turbinia configured project '
                                'turbinia-project. Use gcp_turbinia_import '
                                'recipe to copy the disk into the same '
                                'project.')
    self.assertEqual(is_critical, True)

  @mock.patch('turbinia.client.TurbiniaClient')
  def testWrongSetup(self, _mock_TurbiniaClient): # pylint: disable=invalid-name
    """Tests that invalid setup options generate errors."""
    params = [
        {
            'disk_name': None,
            'project': 'turbinia-project',
            'turbinia_zone': 'europe-west1'
        },
        {
            'disk_name': 'disk-1',
            'project': None,
            'turbinia_zone': 'europe-west1'
        },
        {
            'disk_name': 'disk-1',
            'project': 'turbinia-project',
            'turbinia_zone': None
        }
    ]
    expected_error = ('disk_name, project or turbinia_zone are not all '
                      'specified, bailing out')

    for combination in params:
      test_state = state.DFTimewolfState(config.Config)
      turbinia_processor = turbinia.TurbiniaProcessor(test_state)
      turbinia_processor.setup(**combination)
      self.assertEqual(len(test_state.errors), 1)
      error_msg, is_critical = test_state.errors[0]
      self.assertEqual(error_msg, expected_error)
      self.assertEqual(is_critical, True)

  @mock.patch('os.path.exists')
  @mock.patch('turbinia.output_manager.GCSOutputWriter')
  @mock.patch('turbinia.evidence.GoogleCloudDisk')
  @mock.patch('turbinia.client.TurbiniaClient')
  # pylint: disable=invalid-name
  def testProcess(self,
                  _mock_TurbiniaClient,
                  mock_GoogleCloudDisk,
                  mock_GCSOutputWriter,
                  mock_exists):
    """Tests that the processor processes data correctly."""

    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia.TurbiniaProcessor(test_state)
    turbinia_processor.setup(
        disk_name='disk-1',
        project='turbinia-project',
        turbinia_zone='europe-west1')

    turbinia_processor.client.get_task_data.return_value = [{
        'saved_paths': [
            '/fake/data.plaso',
            '/fake/data2.plaso',
            'gs://bucket/data3.plaso'
        ]
    }]

    # Return true so the tests assumes the above file exists
    mock_exists.return_value = True

    # Our GS path will be downloaded to this fake local path
    local_mock = mock.MagicMock()
    local_mock.copy_from.return_value = '/fake/local/path'
    mock_GCSOutputWriter.return_value = local_mock

    turbinia_processor.process()

    mock_GoogleCloudDisk.assert_called_with(
        disk_name='disk-1',
        project='turbinia-project',
        zone='europe-west1')

    # These are mock classes, so there is a member
    # pylint: disable=no-member
    turbinia_processor.client.send_request.assert_called()
    turbinia_processor.client.get_task_data.assert_called()
    # pylint: disable=protected-access
    mock_GCSOutputWriter.assert_called_with(
        'gs://bucket/data3.plaso',
        local_output_dir=turbinia_processor._output_path
    )
    self.assertEqual(test_state.errors, [])
    self.assertEqual(test_state.output, [
        ('turbinia-project-disk-1', '/fake/data.plaso'),
        ('turbinia-project-disk-1', '/fake/data2.plaso'),
        ('turbinia-project-disk-1', '/fake/local/path')
    ])


if __name__ == '__main__':
  unittest.main()
