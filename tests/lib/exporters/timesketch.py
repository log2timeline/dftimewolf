#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Timesketch exporter."""

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.exporters import timesketch

from dftimewolf import config


class TimesketchExporterTest(unittest.TestCase):
  """Tests for the Timesketch exporter."""

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    timesketch_exporter = timesketch.TimesketchExporter(test_state)
    self.assertIsNotNone(timesketch_exporter)


if __name__ == '__main__':
  unittest.main()
