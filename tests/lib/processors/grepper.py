#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the activity_triage recipe and grepper processor."""

# pytype: disable=attribute-error


from dftimewolf.lib.containers import containers
from dftimewolf.lib.processors import grepper
from tests.lib import modules_test_base


class GrepperTest(modules_test_base.ModuleTestBase):
  """Test case for the grep function. """

  def setUp(self):
    self._InitModule(grepper.GrepperSearch)
    super().setUp()

  def testSingleGrep(self):
    """Test just single keyword grep search on text files."""
    self._module.SetUp(
        keywords='foo|lorem|meow|triage|bar|homebrew'
    )
    # Put here a path to a test directory where you have files to grep on the
    # above keyword. This is to simulate the path received an input from GRR
    self._module.StoreContainer(containers.File(
        name='Test description',
        path='tests/lib/collectors/test_data/grepper_test_dir'
    ))
    self._ProcessModule()
    # pylint: disable=protected-access
    self.assertEqual(
        self._module._keywords, 'foo|lorem|meow|triage|bar|homebrew')

    # pylint: disable=line-too-long
    self.assertEqual(
        self._module._final_output,
        'tests/lib/collectors/test_data/grepper_test_dir/1test.pdf:homebrew\n'
        'tests/lib/collectors/test_data/grepper_test_dir/grepper_test.txt:bar,foo,lorem,triage\n'
        'tests/lib/collectors/test_data/grepper_test_dir/grepper_test2.txt:foo')
