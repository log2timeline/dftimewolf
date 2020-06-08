#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem exporter."""

import unittest
import mock

from dftimewolf.lib import state
from dftimewolf.lib.exporters import scp_ex

from dftimewolf import config


class LocalFileSystemTest(unittest.TestCase):
  """Tests for the local filesystem exporter."""

  def testInitialization(self):
    """Tests that the exporter can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    local_scp_exporter = scp_ex.SCPExporter(test_state)
    self.assertIsNotNone(local_scp_exporter)

  @mock.patch('subprocess.call')
  def testSetup(self, mock_subprocess_call):
    """Tests that the specified directory is used if created."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', True)

    mock_subprocess_call.assert_called_with(
        ['ssh', '-q', '-l', 'fakeuser', 'fakehost', 'true', '-i', 'fakeid'])
    # pylint: disable=protected-access
    self.assertEqual(scp_exporter._destination, '/destination')
    self.assertEqual(scp_exporter._hostname, 'fakehost')
    self.assertEqual(scp_exporter._id_file, 'fakeid')
    self.assertEqual(scp_exporter._paths, ['/path1', '/path2'])
    self.assertEqual(scp_exporter._user, 'fakeuser')

  @mock.patch('subprocess.call')
  def testProcess(self, mock_subprocess_call):
    """Tests that the specified directory is used if created."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', True)
    scp_exporter.Process()

    mock_subprocess_call.assert_called_with(
        ['scp', '/path1', '/path2', 'fakeuser@fakehost:/destination'])

  @mock.patch('subprocess.call')
  def testSetupError(self, mock_subprocess_call):
    """Tests that the specified directory is used if created."""
    mock_subprocess_call.return_value = -1
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', True)

    self.assertEqual(test_state.errors[0], ('Unable to connect to host.', True))

  @mock.patch('subprocess.call')
  def testProcessError(self, mock_subprocess_call):
    """Tests that the specified directory is used if created."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', True)

    mock_subprocess_call.return_value = -1
    scp_exporter.Process()

    self.assertEqual(test_state.errors[0],
                     ("Failed copying ['/path1', '/path2']", True))


if __name__ == '__main__':
  unittest.main()
