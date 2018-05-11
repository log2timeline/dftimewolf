#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem exporter."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.exporters import local_filesystem


class LocalFileSystemTest(unittest.TestCase):
  """Tests for the local filesystem exporter."""

  def testInitialization(self):
    """Tests that the exporter can be initialized."""
    test_state = state.DFTimewolfState()
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    self.assertIsNotNone(local_filesystem_copy)

  def testOutput(self):
    """Tests that the module output is consistent with its input."""
    test_state = state.DFTimewolfState()
    test_state.input = [
      ('First test path', '/fake/test/path1'),
      ('Second test path', '/fake/test/path2')
    ]
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    local_filesystem_copy.setup()

  def testSetup(self):
    """Tests that setup completes correctly."""
    test_state = state.DFTimewolfState()
    local_filesystem_copy = local_filesystem.LocalFilesystemCopy(test_state)
    local_filesystem_copy.setup()
    # pylint: disable=protected-access
    self.assertIsNotNone(local_filesystem_copy._target_directory)


if __name__ == '__main__':
  unittest.main()
