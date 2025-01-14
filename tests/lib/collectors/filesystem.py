#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem collector."""

import unittest

import mock

from dftimewolf.lib.collectors import filesystem
from dftimewolf.lib.containers import containers
from tests.lib import modules_test_base


class LocalFileSystemTest(modules_test_base.ModuleTestBase):
  """Tests for the local filesystem collector."""

  def setUp(self):
    self._InitModule(filesystem.FilesystemCollector)
    super().setUp()

  @mock.patch('os.path.exists')
  def testOutput(self, mock_exists):
    """Tests that the module output is consistent with the input."""
    fake_paths = '/fake/path/1,/fake/path/2'
    self._module.SetUp(paths=fake_paths)
    mock_exists.return_value = True
    self._ProcessModule()
    files = self._module.GetContainers(containers.File)
    self.assertEqual(files[0].path, '/fake/path/1')
    self.assertEqual(files[0].name, '1')
    self.assertEqual(files[1].path, '/fake/path/2')
    self.assertEqual(files[1].name, '2')

if __name__ == '__main__':
  unittest.main()
