#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the AWS logging collector."""

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.collectors import aws_logging

from dftimewolf import config

class AWSLoggingTest(unittest.TestCase):
  """Tests for the AWS logging collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    aws_logging_collector = aws_logging.AWSLogsCollector(test_state)
    self.assertIsNotNone(aws_logging_collector)


if __name__ == '__main__':
  unittest.main()
