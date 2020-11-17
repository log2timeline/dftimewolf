#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the Sanity Checker preflight."""

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.preflights import sanity_checks
from dftimewolf import config


class SanityChecks(unittest.TestCase):
  """Tests for the Sanity Checker preflight."""

  def testInitialization(self):
    test_state = state.DFTimewolfState(config.Config)
    checker = sanity_checks.SanityChecks(test_state)
    self.assertIsNotNone(checker)

  def testInvalidDateOrder(self):
    test_state = state.DFTimewolfState(config.Config)
    checker = sanity_checks.SanityChecks(test_state)

    checker.SetUp(
        startdate='2020-10-31', enddate='2020-10-01', dateformat='%Y-%m-%d')
    checker.Process()

    # The incorrect date order should mean an error was encountered
    self.assertEqual(
        len(checker.state.errors), 1,
        'Date order validation succeeded when it should have failed')

  def testInvalidDateFormat(self):
    test_state = state.DFTimewolfState(config.Config)
    checker = sanity_checks.SanityChecks(test_state)

    checker.SetUp(
        startdate='20-10-01', enddate='20-10-31', dateformat='%Y-%m-%d')
    checker.Process()

    # The incorrect date format should mean an error was encountered
    self.assertEqual(
        len(checker.state.errors), 1,
        'Date format validation succeeded when it should have failed')

  def testValidDates(self):
    test_state = state.DFTimewolfState(config.Config)
    checker = sanity_checks.SanityChecks(test_state)

    checker.SetUp(
        startdate='2020-10-01', enddate='2020-10-31', dateformat='%Y-%m-%d')
    checker.Process()

    # All good - should be no errors
    self.assertEqual(
        len(checker.state.errors), 0, 'Date order validation failure')

if __name__ == '__main__':
  unittest.main()
