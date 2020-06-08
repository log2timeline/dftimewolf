#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem exporter."""

import unittest
import mock

from dftimewolf.lib import state
from dftimewolf.lib.exporters import local_filesystem

from dftimewolf import config


FAKE_PATHS = {
    '/fake/evidence_directory': ['file1', 'file2'],
    '/fake/evidence_file': None
}


def FakeIsDir(string):
  """Fake isdir function for mocking purposes."""
  return bool(FAKE_PATHS[string])


def FakeListDir(string):
  """Fake listdir function for mocking purposes."""
  return FAKE_PATHS[string]


class LocalFileSystemTest(unittest.TestCase):
  """Tests for the local filesystem exporter."""

  def testInitialization(self):
    """Tests that the exporter can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    self.assertIsNotNone(local_filesystem_copy)

  @mock.patch('shutil.copytree')
  @mock.patch('shutil.copy2')
  @mock.patch('os.path.isdir', side_effect=FakeIsDir)
  @mock.patch('os.listdir', side_effect=FakeListDir)
  @mock.patch('tempfile.mkdtemp')
  # pylint: disable=unused-argument
  def testProcess(self,
                  mock_mkdtemp,
                  unused_mocklistdir,
                  unused_mockisdir,
                  mock_copy2,
                  mock_copytree):
    """Tests that the module processes input correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.input = [
        ('description', '/fake/evidence_directory'),
        ('description2', '/fake/evidence_file'),
    ]
    mock_mkdtemp.return_value = '/fake/random'
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    local_filesystem_copy.SetUp()
    local_filesystem_copy.Process()
    mock_copytree.assert_has_calls([
        mock.call('/fake/evidence_directory/file1', '/fake/random/file1'),
        mock.call('/fake/evidence_directory/file2', '/fake/random/file2'),
    ])
    mock_copy2.assert_called_with('/fake/evidence_file', '/fake/random')

  @mock.patch('tempfile.mkdtemp')
  def testSetup(self, mock_mkdtemp):
    """Tests that the specified directory is used if created."""
    mock_mkdtemp.return_value = '/fake/random'
    test_state = state.DFTimewolfState(config.Config)
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    local_filesystem_copy.SetUp()
    # pylint: disable=protected-access
    self.assertEqual(local_filesystem_copy._target_directory, '/fake/random')

  @mock.patch('os.makedirs')
  def testSetupError(self, mock_makedirs):
    """Tests that an error is generated if target_directory is unavailable."""
    mock_makedirs.side_effect = OSError('FAKEERROR')
    test_state = state.DFTimewolfState(config.Config)
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    with self.assertRaises(OSError) as exception:
      local_filesystem_copy.SetUp(target_directory="/nonexistent")
      self.assertEqual(str(exception), 'FAKEERROR')

  @mock.patch('os.makedirs')
  def testSetupManualDir(self, mock_makedirs):
    """Tests that the specified directory is used if created."""
    mock_makedirs.return_value = True
    test_state = state.DFTimewolfState(config.Config)
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    local_filesystem_copy.SetUp(target_directory='/nonexistent')
    # pylint: disable=protected-access
    self.assertEqual(local_filesystem_copy._target_directory, '/nonexistent')


if __name__ == '__main__':
  unittest.main()
