#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the recipes manager."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import resources
from dftimewolf.lib.recipes import manager


class TestRecipe(resources.Recipe):
  """Test recipe."""

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

  def __init__(self):
    """Initializes a test recipe."""
    super(TestRecipe, self).__init__(
        self._DESCRIPTION, self._CONTENTS, self._ARGS)


class RecipesManagerTest(unittest.TestCase):
  """Tests for the recipes manager."""

  def testRecipeRegistration(self):
    """Tests the RegisterRecipe and DeregisterRecipe functions."""
    test_recipe = TestRecipe()

    # pylint: disable=protected-access
    number_of_recipes = len(manager.RecipesManager._recipes)

    manager.RecipesManager.RegisterRecipe(test_recipe)
    self.assertEqual(
        len(manager.RecipesManager._recipes), number_of_recipes + 1)

    with self.assertRaises(KeyError):
      manager.RecipesManager.RegisterRecipe(test_recipe)

    manager.RecipesManager.DeregisterRecipe(test_recipe)
    self.assertEqual(len(manager.RecipesManager._recipes), number_of_recipes)

  def testGetRecipes(self):
    """Tests the GetRecipes function."""
    test_recipe = TestRecipe()

    manager.RecipesManager.RegisterRecipe(test_recipe)

    registered_recipes = manager.RecipesManager.GetRecipes()
    self.assertEqual(registered_recipes, [test_recipe])

    manager.RecipesManager.DeregisterRecipe(test_recipe)

  def testRegisterRecipes(self):
    """Tests the RegisterRecipes function."""
    test_recipe = TestRecipe()

    # pylint: disable=protected-access
    number_of_recipes = len(manager.RecipesManager._recipes)

    manager.RecipesManager.RegisterRecipes([test_recipe])
    self.assertEqual(
        len(manager.RecipesManager._recipes), number_of_recipes + 1)

    manager.RecipesManager.DeregisterRecipe(test_recipe)


if __name__ == '__main__':
  unittest.main()
