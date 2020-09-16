#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the localplaso processor."""

import unittest
import mock

from dftimewolf.lib import state
from dftimewolf.lib.processors import localplaso
from dftimewolf.lib.containers import containers

from dftimewolf import config


class LocalPlasoTest(unittest.TestCase):
  """Tests for the local Plaso processor."""

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    local_plaso_processor = localplaso.LocalPlasoProcessor(test_state)
    self.assertIsNotNone(local_plaso_processor)

  # pylint: disable=invalid-name
  @mock.patch('subprocess.Popen')
  def testProcessing(self, mock_Popen):
    """Tests that the correct number of containers is added."""
    test_state = state.DFTimewolfState(config.Config)
    mock_popen_object = mock.Mock()
    mock_popen_object.communicate.return_value = (None, None)
    mock_popen_object.wait.return_value = False
    mock_Popen.return_value = mock_popen_object

    local_plaso_processor = localplaso.LocalPlasoProcessor(test_state)
    test_state.StoreContainer(
        containers.File(name='test', path='/notexist/test'))
    local_plaso_processor.SetUp()
    local_plaso_processor.Process()
    mock_Popen.assert_called_once()
    args = mock_Popen.call_args[0][0] # Get positional arguments of first call
    self.assertEqual(args[9], '/notexist/test')
    plaso_path = args[8] # Dynamically generated path to the plaso file
    self.assertEqual(
        test_state.GetContainers(containers.File)[0].path,
        plaso_path)

if __name__ == '__main__':
  unittest.main()
