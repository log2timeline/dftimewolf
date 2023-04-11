#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Turbinia processor."""

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
from dftimewolf.lib.containers import containers
from dftimewolf import config

HAS_TURBINIA = False

try:
  from dftimewolf.lib.processors import turbinia_artifact_legacy
  from turbinia import config as turbinia_config
  from turbinia import message as turbinia_message
  # Manually set TURBINIA_PROJECT to the value we expect.
  turbinia_config.TURBINIA_PROJECT = 'turbinia-project'
  HAS_TURBINIA = True
except ImportError:
  pass

YARA_RULE = """rule dummy { condition: false }"""

@unittest.skipIf(not HAS_TURBINIA, 'Missing Turbinia dependency.')
class TurbiniaArtifactProcessorTest(unittest.TestCase):
  """Tests for the Turbinia processor."""

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia_artifact_legacy.TurbiniaArtifactProcessor(
        test_state)
    self.assertIsNotNone(turbinia_processor)

  @mock.patch('turbinia.client.get_turbinia_client')
  # pylint: disable=invalid-name
  def testSetup(self, _mock_TurbiniaClient):
    """Tests that the processor is set up correctly."""
    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia_artifact_legacy.TurbiniaArtifactProcessor(
        test_state)
    turbinia_processor.SetUp(
        turbinia_config_file=None,
        project='turbinia-project',
        turbinia_recipe=None,
        turbinia_zone='europe-west1',
        output_directory='/tmp/outputdir',
        sketch_id=123)
    # pylint: disable=line-too-long
    turbinia_processor.client.create_request.return_value = turbinia_message.TurbiniaRequest()
    self.assertEqual(turbinia_processor.project, 'turbinia-project')
    self.assertEqual(turbinia_processor.turbinia_recipe, None)
    self.assertEqual(turbinia_processor.turbinia_zone, 'europe-west1')
    self.assertEqual(turbinia_processor.sketch_id, 123)
    self.assertEqual(turbinia_processor.output_directory, '/tmp/outputdir')
    self.assertEqual(test_state.errors, [])

    # pylint: disable=protected-access
    six.assertRegex(
        self, turbinia_processor._output_path, '(/tmp/tmp|/var/folders).+')

  @mock.patch('turbinia.client.get_turbinia_client')
  # pylint: disable=invalid-name
  def testProcess(self, _mock_TurbiniaClient):
    """Tests that the processor processes data correctly when a GCEDisk is
        received from the state.
    """
    test_state = state.DFTimewolfState(config.Config)
    turbinia_processor = turbinia_artifact_legacy.TurbiniaArtifactProcessor(
      test_state)
    turbinia_processor.StoreContainer(
        containers.RemoteFSPath(hostname='remotehost', path='/tmp/file.ext'))
    turbinia_processor.SetUp(
        turbinia_config_file=None,
        project='turbinia-project',
        turbinia_recipe=None,
        turbinia_zone='europe-west1',
        output_directory='/tmp/outputdir',
        sketch_id=123)
    # pylint: disable=line-too-long
    turbinia_processor.client.create_request.return_value = turbinia_message.TurbiniaRequest()
    turbinia_processor.client.get_task_data.return_value = [{
        'saved_paths': [
            '/fake/data.plaso',
            '/fake/data2.plaso',
            '/another/random/file.txt',
            'gs://BinaryExtractorTask.tar.gz',
        ],
        'name': 'TaskName'
    }]

    turbinia_processor.PreProcess()
    in_containers = turbinia_processor.GetContainers(
        turbinia_processor.GetThreadOnContainerType(), pop=True)
    for c in in_containers:
      turbinia_processor.Process(c)  # pytype: disable=wrong-arg-types
      # GetContainers returns the abstract base class type, but process is
      # called with the instantiated child class.
    turbinia_processor.PostProcess()

    conts = turbinia_processor.GetContainers(containers.RemoteFSPath)
    self.assertEqual(len(conts), 2)
    for c in conts:
      self.assertEqual(c.hostname, 'remotehost')
      self.assertIn(c.path, ['/fake/data.plaso', '/fake/data2.plaso'])


if __name__ == '__main__':
  unittest.main()
