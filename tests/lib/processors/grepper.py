#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the activity_triage recipe and grepper processor."""

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.processors import grepper

from dftimewolf import config


class GrepperTest(unittest.TestCase):
  """Test case for the grep function. """

  def TestSingleGrep(self):
    """Test just single keyword grep search on text files."""
    test_state = state.DFTimewolfState(config.Config)
    base_grepper_search = grepper.GrepperSearch(test_state)
    base_grepper_search.SetUp(
        keywords='foo|lorem|meow|triage|bar|homebrew'
    )
    # Put here a path to a test directory where you have files to grep on the
    # above keyword. This is to simulate the path received an input from GRR
    base_grepper_search.state.input = \
      [['Test description', '../collectors/test_data/grepper_test_dir']]
    base_grepper_search.Process()
    # pylint: disable=protected-access
    self.assertEqual(
        base_grepper_search._keywords, 'foo|lorem|meow|triage|bar|homebrew')

    self.assertEqual(
        base_grepper_search._final_output,
        '../collectors/test_data/grepper_test_dir/grepper_test.txt:bar,foo,'
        'lorem,triage\n'
        '../collectors/test_data/grepper_test_dir/1test.pdf:homebrew\n'
        '../collectors/test_data/grepper_test_dir/grepper_test2.txt:foo')
