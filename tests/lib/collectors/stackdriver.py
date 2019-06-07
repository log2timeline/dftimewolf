#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Stackdriver collector."""

from __future__ import unicode_literals

import unittest


from dftimewolf.lib import state
from dftimewolf.lib.collectors import stackdriver

from dftimewolf import config

class StackdriverTest(unittest.TestCase):
  """Tests for the Stackdriver collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    stackdriver_collector = stackdriver.StackdriverLogsCollector(test_state)
    self.assertIsNotNone(stackdriver_collector)


if __name__ == '__main__':
  unittest.main()
