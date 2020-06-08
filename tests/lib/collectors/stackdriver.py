#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Google Cloud Platform (GCP) logging collector."""

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.collectors import gcp_logging

from dftimewolf import config

class GCPLoggingTest(unittest.TestCase):
  """Tests for the GCP logging collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    gcp_logging_collector = gcp_logging.GCPLogsCollector(test_state)
    self.assertIsNotNone(gcp_logging_collector)


if __name__ == '__main__':
  unittest.main()
