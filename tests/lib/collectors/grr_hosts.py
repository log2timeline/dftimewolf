#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR host collectors."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.collectors import grr_hosts


class GRRArtifactCollectorTest(unittest.TestCase):
  """Tests for the GRR artifact collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_artifact_collector = grr_hosts.GRRArtifactCollector(test_state)
    self.assertIsNotNone(grr_artifact_collector)

class GRRFileCollectorTest(unittest.TestCase):
  """Tests for the GRR file collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_file_collector = grr_hosts.GRRFileCollector(test_state)
    self.assertIsNotNone(grr_file_collector)


class GRRFlowCollector(unittest.TestCase):
  """Tests for the GRR flow collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_flow_collector = grr_hosts.GRRFlowCollector(test_state)
    self.assertIsNotNone(grr_flow_collector)


if __name__ == '__main__':
  unittest.main()
