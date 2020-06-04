#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the activity_triage recipe and grepper processor."""

import unittest

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.processors import grepper


class GrepperTest(unittest.TestCase):
  """Test case for the grep function. """

  def testSingleGrep(self):
    """Test just single keyword grep search on text files."""
    test_state = state.DFTimewolfState(config.Config)
    base_grepper_search = grepper.GrepperSearch(test_state)
    base_grepper_search.SetUp(
        keywords='foo|lorem|meow|triage|bar|homebrew'
    )
    # Put here a path to a test directory where you have files to grep on the
    # above keyword. This is to simulate the path received an input from GRR
    test_state.StoreContainer(containers.File(
      name='Test description',
      path='tests/lib/collectors/test_data/grepper_test_dir'
    ))
    base_grepper_search.Process()
    # pylint: disable=protected-access
    self.assertEqual(
        base_grepper_search._keywords, 'foo|lorem|meow|triage|bar|homebrew')

    # pylint: disable=line-too-long
    self.assertEqual(
        base_grepper_search._final_output,
        'tests/lib/collectors/test_data/grepper_test_dir/grepper_test.txt:bar,foo,lorem,triage\n'
        'tests/lib/collectors/test_data/grepper_test_dir/1test.pdf:homebrew\n'
        'tests/lib/collectors/test_data/grepper_test_dir/grepper_test2.txt:foo')
