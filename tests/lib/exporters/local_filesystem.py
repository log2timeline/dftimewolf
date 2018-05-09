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
    local_plaso_processor = local_filesystem.LocalFilesystemCopy(test_state)
    self.assertIsNotNone(local_plaso_processor)


if __name__ == '__main__':
  unittest.main()
