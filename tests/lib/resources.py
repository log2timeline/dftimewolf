#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the various dfTimewolf resource objects."""

import unittest

from dftimewolf.lib import resources


class RecipeTest(unittest.TestCase):
  """Tests Recipe."""

  _ARGS = [
      ('test', 'Test argument', None),
  ]

  _CONTENTS = {
      'name': 'test',
      'short_description': 'recipe description',
      'modules': [{
          'wants': [],
          'name': 'TestModule',
          'args': {
              'test': '@test'
          },
      }],
  }

  _DESCRIPTION = 'test recipe'

  def testInitialize(self):
    """Tests the __init__ function."""
    recipe = resources.Recipe(self._DESCRIPTION, self._CONTENTS, self._ARGS)
    self.assertIsNotNone(recipe)

  def testGetHelpString(self):
    """Tests the GetHelpString function."""
    recipe = resources.Recipe(self._DESCRIPTION, self._CONTENTS, self._ARGS)

    expected_help_string = (
        ' test                               recipe description\n')
    help_string = recipe.GetHelpString()
    self.assertEqual(help_string, expected_help_string)


if __name__ == '__main__':
  unittest.main()
