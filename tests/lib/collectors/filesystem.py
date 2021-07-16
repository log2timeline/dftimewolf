#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem collector."""

import unittest

import mock

from dftimewolf.lib import state
from dftimewolf.lib.collectors import filesystem
from dftimewolf.lib.containers import containers

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
    """Tests that the module output is consistent with the input."""
    test_state = state.DFTimewolfState(config.Config)
    filesystem_collector = filesystem.FilesystemCollector(test_state)
    fake_paths = '/fake/path/1,/fake/path/2'
    filesystem_collector.SetUp(paths=fake_paths)
    mock_exists.return_value = True
    filesystem_collector.Process()
    files = test_state.GetContainers(containers.File)
    self.assertEqual(files[0].path, '/fake/path/1')
    self.assertEqual(files[0].name, '1')
    self.assertEqual(files[1].path, '/fake/path/2')
    self.assertEqual(files[1].name, '2')

  unittest.main()
