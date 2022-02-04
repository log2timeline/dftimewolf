#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem exporter."""

import unittest

import mock

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib import errors
from dftimewolf.lib.containers import containers
from dftimewolf.lib.exporters import local_filesystem

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
  def testProcessCopy(self,
                      mock_mkdtemp,
                      unused_mocklistdir,
                      unused_mockisdir,
                      mock_copy2,
                      mock_copytree):
    """Tests that the module processes input and copies correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.StoreContainer(containers.File(
        name='description', path='/fake/evidence_directory'))
    test_state.StoreContainer(containers.File(
        name='description2', path='/fake/evidence_file'))
    mock_mkdtemp.return_value = '/fake/random'

    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    local_filesystem_copy.SetUp()
    local_filesystem_copy.Process()

    mock_copytree.assert_has_calls([
        mock.call('/fake/evidence_directory',
            '/fake/random'),
    ])
    mock_copy2.assert_called_with('/fake/evidence_file', '/fake/random')

  @mock.patch('dftimewolf.lib.utils.Compress')
  @mock.patch('tempfile.mkdtemp')
  def testProcessCompress(self, mock_mkdtemp, mock_compress):
    """Tests that the module processes input and compresses correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.StoreContainer(containers.File(
        name='description', path='/fake/evidence_directory'))
    test_state.StoreContainer(containers.File(
        name='description2', path='/fake/evidence_file'))
    mock_mkdtemp.return_value = '/fake/random'
    mock_compress.return_value = '/fake/tarball.tgz'
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    local_filesystem_copy.SetUp(compress=True)
    local_filesystem_copy.Process()
    mock_compress.assert_has_calls([
        mock.call('/fake/evidence_directory', '/fake/random'),
        mock.call('/fake/evidence_file', '/fake/random'),
    ])

  @mock.patch('tempfile.mkdtemp')
  def testSetup(self, mock_mkdtemp):
    """Tests that the specified directory is used if created."""
    mock_mkdtemp.return_value = '/fake/random'
    test_state = state.DFTimewolfState(config.Config)
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    local_filesystem_copy.SetUp()
    # pylint: disable=protected-access
    self.assertEqual(local_filesystem_copy._target_directory, '/fake/random')

  @mock.patch('os.path.isdir')
  @mock.patch('shutil.copytree')
  def testSetupError(self, mock_copytree, mock_isdir):
    """Tests that an error is generated if target_directory is unavailable."""
    mock_copytree.side_effect = OSError('FAKEERROR')
    mock_isdir.return_value = False
    test_state = state.DFTimewolfState(config.Config)
    test_state.StoreContainer(
        containers.File(name='blah', path='/sourcefile'))
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    local_filesystem_copy.SetUp(target_directory="/nonexistent")
    with self.assertRaises(errors.DFTimewolfError) as error:
      local_filesystem_copy.Process()
    self.assertEqual(len(test_state.errors), 1)
    self.assertEqual(test_state.errors[0], error.exception)

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
