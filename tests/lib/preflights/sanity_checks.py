#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the Sanity Checker preflight."""

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.errors import DFTimewolfError
from dftimewolf.lib.preflights import sanity_checks
from dftimewolf import config


class SanityChecks(unittest.TestCase):
  """Tests for the Sanity Checker preflight."""

  def testInitialization(self):
    """Test initialisation of the sanity checker."""
    test_state = state.DFTimewolfState(config.Config)
    checker = sanity_checks.SanityChecks(test_state)
    self.assertIsNotNone(checker)

  def testInvalidDateOrder(self):
    """Test that dates in the incorrect order produces an error."""
    test_state = state.DFTimewolfState(config.Config)
    checker = sanity_checks.SanityChecks(test_state)

    start_date = '2020-10-31'
    end_date = '2020-10-01'
    expected_error = sanity_checks.DATE_ORDER_ERROR_STRING.format(
        start_date, end_date)

    try:
      checker.SetUp(
          startdate=start_date, enddate=end_date, dateformat='%Y-%m-%d')
      checker.Process()
    except (DFTimewolfError) as exception:
      self.assertEqual(str(exception), expected_error,
          'Exception differs from expected')

  def testInvalidDateFormat(self):
    """Test that invalid date formats produce an error."""
    test_state = state.DFTimewolfState(config.Config)
    checker = sanity_checks.SanityChecks(test_state)

    try:
      checker.SetUp(
          startdate='20-10-01', enddate='20-10-31', dateformat='%Y-%m-%d')
      checker.Process()
    except (DFTimewolfError) as exception:
      self.assertEqual(str(exception),
          "time data '20-10-01' does not match format '%Y-%m-%d'",
          'Error message differs from expected')

  def testValidDates(self):
    """Test that valid dates produce no error."""
    test_state = state.DFTimewolfState(config.Config)
    checker = sanity_checks.SanityChecks(test_state)

    checker.SetUp(
        startdate='2020-10-01', enddate='2020-10-31', dateformat='%Y-%m-%d')
    checker.Process()

    # All good - should be no errors - though we should never reach this
    # in an error as checker.Process() throws an exception
    self.assertEqual(
        len(checker.state.errors), 0, 'Date order validation failure')

if __name__ == '__main__':
  unittest.main()
