#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the localplaso processor."""

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.processors import localplaso

from dftimewolf import config


class LocalPlasoTest(unittest.TestCase):
  """Tests for the local Plaso processor."""

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    local_plaso_processor = localplaso.LocalPlasoProcessor(test_state)
    self.assertIsNotNone(local_plaso_processor)


if __name__ == '__main__':
  unittest.main()
