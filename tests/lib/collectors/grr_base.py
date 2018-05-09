#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR base collector."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.collectors import grr_base


class GRRBaseModuleTest(unittest.TestCase):
  """Tests for the GRR base collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_base_module = grr_base.GRRBaseModule(test_state)
    self.assertIsNotNone(grr_base_module)


if __name__ == '__main__':
  unittest.main()
