#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem collector."""

import unittest

import mock

from dftimewolf.lib import state
from dftimewolf.lib.collectors import filesystem

from dftimewolf import config

class LocalFileSystemTest(unittest.TestCase):
  """Tests for the local filesystem collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    filesystem_collector = filesystem.FilesystemCollector(test_state)
    self.assertIsNotNone(filesystem_collector)

  @mock.patch('os.path.exists')
  def testOutput(self, mock_exists):
    """Tests that the module ouput is consistent with the input."""
    test_state = state.DFTimewolfState(config.Config)
    filesystem_collector = filesystem.FilesystemCollector(test_state)
    fake_paths = '/fake/path/1,/fake/path/2'
    filesystem_collector.SetUp(paths=fake_paths)
    mock_exists.return_value = True
    filesystem_collector.Process()
    expected_output = [
        ('1', '/fake/path/1'),
        ('2', '/fake/path/2')
    ]
    self.assertEqual(test_state.output, expected_output)

  @mock.patch('dftimewolf.lib.state.DFTimewolfState.AddError')
  def testSetup(self, mock_add_error):
    """Tests that no paths specified in setup will generate an error."""
    test_state = state.DFTimewolfState(config.Config)
    filesystem_collector = filesystem.FilesystemCollector(test_state)
    filesystem_collector.SetUp(paths=None)
    mock_add_error.assert_called_with(
        'No `paths` argument provided in recipe, bailing', critical=True)
    self.assertIsNone(filesystem_collector._paths)  # pylint: disable=protected-access

if __name__ == '__main__':
  unittest.main()
