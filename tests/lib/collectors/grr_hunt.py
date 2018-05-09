#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR hunt collectors."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.collectors import grr_hunt


class GRRArtifactCollectorTest(unittest.TestCase):
  """Tests for the GRR artifact collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_hunt_artifact_collector = grr_hunt.GRRHuntArtifactCollector(test_state)
    self.assertIsNotNone(grr_hunt_artifact_collector)


class GRRFileCollectorTest(unittest.TestCase):
  """Tests for the GRR file collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_hunt_file_collector = grr_hunt.GRRHuntFileCollector(test_state)
    self.assertIsNotNone(grr_hunt_file_collector)


class GRRFHuntDownloader(unittest.TestCase):
  """Tests for the GRR hunt downloader."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_hunt_downloader = grr_hunt.GRRHuntDownloader(test_state)
    self.assertIsNotNone(grr_hunt_downloader)


if __name__ == '__main__':
  unittest.main()
