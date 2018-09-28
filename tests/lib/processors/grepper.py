#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR host collectors."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.processors import grepper

class GrepperTest(unittest.TestCase):
  """Test case for the grep function. """

  def TestSingleGrep(self):
    """Test just single keyword grep search on text files."""
    test_state = state.DFTimewolfState()
    base_grepper_search = grepper.GrepperSearch(test_state)
    base_grepper_search.setup(
        keywords='foo|pycharm|CE'
    )
    # Put here a path to a test directory where you have files to grep on the
    # above keyword. This is to simulate the path received an input from GRR
    base_grepper_search.state.input = [['Test description',
      '/testdir/triager-test']]
    base_grepper_search.process()
    # pylint: disable=protected-access
    self.assertEqual(base_grepper_search._keywords, 'foo|pycharm|CE')
