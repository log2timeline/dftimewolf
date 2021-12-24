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
      'preflights': [{
          "wants": [],
          "name": "TestPreflight",
          "args": {}
      }],
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

  def testGetShortDescriptionString(self):
    """Tests the GetShortDescriptionString function."""
    recipe = resources.Recipe(self._DESCRIPTION, self._CONTENTS, self._ARGS)

    expected_help_string = (
        ' test                               recipe description\n')
    help_string = recipe.GetShortDescriptionString()
    self.assertEqual(help_string, expected_help_string)

  def testGetModuleNames(self):
    recipe = resources.Recipe(self._DESCRIPTION, self._CONTENTS, self._ARGS)
    module_names = recipe.GetModuleNames()
    self.assertEqual(['TestModule'], module_names)

  def testGetPreflightNames(self):
    recipe = resources.Recipe(self._DESCRIPTION, self._CONTENTS, self._ARGS)
    preflight_names = recipe.GetPreflightNames()
    self.assertEqual(['TestPreflight'], preflight_names)


if __name__ == '__main__':
  unittest.main()
