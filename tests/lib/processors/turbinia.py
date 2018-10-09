#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Turbinia processor."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.processors import turbinia


class TurbiniaProcessorTest(unittest.TestCase):
  """Tests for the Turbinia processor."""

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    test_state = state.DFTimewolfState()
    turbinia_processor = turbinia.TurbiniaProcessor(test_state)
    self.assertIsNotNone(turbinia_processor)


if __name__ == '__main__':
  unittest.main()
