#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem collector."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.collectors import filesystem


class LocalFileSystemTest(unittest.TestCase):
  """Tests for the local filesystem collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    filesystem_collector = filesystem.FilesystemCollector(test_state)
    self.assertIsNotNone(filesystem_collector)


if __name__ == '__main__':
  unittest.main()
