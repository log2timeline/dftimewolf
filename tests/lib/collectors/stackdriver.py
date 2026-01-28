#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Google Cloud Platform (GCP) logging collector."""

import unittest
from unittest import mock

from dftimewolf.lib.collectors import gcp_logging


class GCPLoggingTest(unittest.TestCase):
  """Tests for the GCP logging collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    gcp_logging_collector = gcp_logging.GCPLogsCollector(
        name='',
        cache_=mock.MagicMock(),
        container_manager_=mock.MagicMock(),
        telemetry_=mock.MagicMock(),
        publish_message_callback=mock.MagicMock())
    self.assertIsNotNone(gcp_logging_collector)


if __name__ == '__main__':
  unittest.main()
