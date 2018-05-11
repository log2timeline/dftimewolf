#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem collector."""

from __future__ import unicode_literals

import unittest

import mock

from dftimewolf.lib import state
from dftimewolf.lib.collectors import filesystem


class LocalFileSystemTest(unittest.TestCase):
  """Tests for the local filesystem collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    filesystem_collector = filesystem.FilesystemCollector(test_state)
    self.assertIsNotNone(filesystem_collector)

  @mock.patch('dftimewolf.lib.collectors.filesystem.os.path')
  def testOutput(self, mock_path):
    """Tests that the module ouput is consistent with the input."""
    test_state = state.DFTimewolfState()
    filesystem_collector = filesystem.FilesystemCollector(test_state)
    fake_paths = '/fake/path/1,/fake/path/2'
    filesystem_collector.setup(paths=fake_paths)
    mock_path.exists.return_value = True
    filesystem_collector.process()
    expected_output = [
        ('/fake/path/1', '/fake/path/1'),
        ('/fake/path/2', '/fake/path/2')
    ]
    self.assertEqual(test_state.output, expected_output)

  @mock.patch('dftimewolf.lib.state.DFTimewolfState.add_error')
  def testSetup(self, mock_add_error):
    """Tests that no paths specified in setup will generate an error."""
    test_state = state.DFTimewolfState()
    filesystem_collector = filesystem.FilesystemCollector(test_state)
    filesystem_collector.setup(paths=None)
    mock_add_error.assert_called_with(
        'No `paths` argument provided in recipe, bailing', critical=True)
    self.assertIsNone(filesystem_collector._paths)  # pylint: disable=protected-access

if __name__ == '__main__':
  unittest.main()
