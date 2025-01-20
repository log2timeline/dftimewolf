#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem exporter."""

import unittest

import mock

from dftimewolf.lib import errors
from dftimewolf.lib.containers import containers
from dftimewolf.lib.exporters import local_filesystem
from tests.lib import modules_test_base


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


class LocalFileSystemTest(modules_test_base.ModuleTestBase):
  """Tests for the local filesystem exporter."""

  # For Pytype
  _module: local_filesystem.LocalFilesystemCopy

  def setUp(self):
    self._InitModule(local_filesystem.LocalFilesystemCopy)
    super().setUp()

  @mock.patch('shutil.copytree', autospec=True)
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
    mock_copytree.return_value = '/fake/destination'
    mock_copy2.return_value = '/fake/destination'

    self._module.StoreContainer(containers.File(
        name='description', path='/fake/evidence_directory'))
    self._module.StoreContainer(containers.File(
        name='description2', path='/fake/evidence_file'))
    mock_mkdtemp.return_value = '/fake/destination'

    self._module.SetUp()
    self._ProcessModule()

    mock_copytree.assert_has_calls([
        mock.call('/fake/evidence_directory',
                  '/fake/destination/evidence_directory',
                  dirs_exist_ok=True)
    ])
    mock_copy2.assert_called_with('/fake/evidence_file', '/fake/destination')

  @mock.patch('dftimewolf.lib.utils.Compress')
  @mock.patch('tempfile.mkdtemp')
  def testProcessCompress(self, mock_mkdtemp, mock_compress):
    """Tests that the module processes input and compresses correctly."""
    self._module.StoreContainer(containers.File(
        name='description', path='/fake/evidence_directory'))
    self._module.StoreContainer(containers.File(
        name='description2', path='/fake/evidence_file'))
    mock_mkdtemp.return_value = '/fake/random'
    mock_compress.return_value = '/fake/tarball.tgz'
    self._module.SetUp(compress=True)
    self._ProcessModule()
    mock_compress.assert_has_calls([
        mock.call('/fake/evidence_directory', '/fake/random'),
        mock.call('/fake/evidence_file', '/fake/random'),
    ])

  @mock.patch('tempfile.mkdtemp')
  def testSetup(self, mock_mkdtemp):
    """Tests that the specified directory is used if created."""
    mock_mkdtemp.return_value = '/fake/random'
    self._module.SetUp()
    # pylint: disable=protected-access
    self.assertEqual(self._module._target_directory, '/fake/random')

  @mock.patch('os.path.isdir')
  @mock.patch('shutil.copytree')
  def testSetupError(self, mock_copytree, mock_isdir):
    """Tests that an error is generated if target_directory is unavailable."""
    mock_copytree.side_effect = OSError('FAKEERROR')
    mock_isdir.return_value = False
    self._module.StoreContainer(
        containers.File(name='blah', path='/sourcefile'))
    self._module.SetUp(target_directory="/nonexistent")
    with self.assertRaises(errors.DFTimewolfError):
      self._ProcessModule()

  @mock.patch('os.makedirs')
  def testSetupManualDir(self, mock_makedirs):
    """Tests that the specified directory is used if created."""
    mock_makedirs.return_value = True
    self._module.SetUp(target_directory='/nonexistent')
    # pylint: disable=protected-access
    self.assertEqual(self._module._target_directory, '/nonexistent')


if __name__ == '__main__':
  unittest.main()
