#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the SSH multiplexer preflight."""

import unittest
import mock

from dftimewolf.lib import state
from dftimewolf.lib.preflights.sanity_checks import SanityChecks
from dftimewolf import config


class SanityChecks(unittest.TestCase):
  """Tests for the Sanity Checker preflight."""

  def testInitialization(self):
    test_state = state.DFTimewolfState(config.Config)
    checker = SanityChecks(test_state)
    self.assertIsNotNone(checker)

  def testInvalidDateOrder(self):
    test_state = state.DFTimewolfState(config.Config)
    checker = SanityChecks(test_state)

    checker.SetUp(
        startdate='2020-10-31', enddate='2020-10-01', dateformat='%Y-%m-%d')
    checker.Process()

    # The incorrect date order should mean an error was encountered
    self.assertLen(
        checker.state.errors, 1,
        'Date order validation succeeded when it should have failed')

  def testInvalidDateFormat(self):
    test_state = state.DFTimewolfState(config.Config)
    checker = SanityChecks(test_state)

    checker.SetUp(
        startdate='20-10-01', enddate='20-10-31', dateformat='%Y-%m-%d')
    checker.Process()

    # The incorrect date format should mean an error was encountered
    self.assertLen(
        checker.state.errors, 1,
        'Date format validation succeeded when it should have failed')

  def testValidDates(self):
    test_state = state.DFTimewolfState(config.Config)
    checker = SanityChecks(test_state)

    checker.SetUp(
        startdate='2020-10-01', enddate='2020-10-31', dateformat='%Y-%m-%d')
    checker.Process()

    # All good - should be no errors
    self.assertEmpty(checker.state.errors, 'Date order validation failure')

if __name__ == '__main__':
  unittest.main()
