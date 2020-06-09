#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the recipes manager."""

import io
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

  # pylint: disable=protected-access

  _JSON = """{
    "name": "test",
    "description": "test recipe",
    "short_description": "recipe description",
    "modules": [{
        "wants": [],
        "name": "TestModule",
        "args": {
            "test": "@test"
        }
    }],
    "args": [
      ["test", "Test argument", null]
    ]
}
"""

  def setUp(self):
    manager.RecipesManager.ALLOW_RECIPE_OVERRIDE = False

  def testReadRecipeFromFileObject(self):
    """Tests the _ReadRecipeFromFileObject function."""
    test_manager = manager.RecipesManager()

    recipe = test_manager._ReadRecipeFromFileObject(io.StringIO(self._JSON))

    self.assertIsNotNone(recipe)
    self.assertEqual(recipe.name, 'test')
    self.assertEqual(recipe.description, 'test recipe')
    self.assertEqual(recipe.contents['modules'][0]['name'], 'TestModule')
    self.assertEqual(len(recipe.args), 1)

  # TODO: add tests for ReadRecipesFromDirectory.

  def testRecipeRegistration(self):
    """Tests the RegisterRecipe and DeregisterRecipe functions."""
    test_manager = manager.RecipesManager()

    test_recipe = TestRecipe()

    number_of_recipes = len(test_manager._recipes)

    test_manager.RegisterRecipe(test_recipe)
    self.assertEqual(len(test_manager._recipes), number_of_recipes + 1)

    with self.assertRaises(KeyError):
      test_manager.RegisterRecipe(test_recipe)

    test_manager.DeregisterRecipe(test_recipe)
    self.assertEqual(len(test_manager._recipes), number_of_recipes)

  def testOverrideRecipeRegistration(self):
    """Tests the RegisterRecipe with override functionality."""
    manager.RecipesManager.ALLOW_RECIPE_OVERRIDE = True
    test_manager = manager.RecipesManager()

    test_recipe = TestRecipe()

    number_of_recipes = len(test_manager._recipes)

    test_manager.RegisterRecipe(test_recipe)
    self.assertEqual(len(test_manager._recipes), number_of_recipes + 1)

    override = TestRecipe()
    override.description = 'override'
    test_manager.RegisterRecipe(override)

    self.assertEqual(len(test_manager._recipes), number_of_recipes + 1)
    self.assertEqual(test_manager._recipes['test'].description, 'override')

    test_manager.DeregisterRecipe(override)

  def testGetRecipes(self):
    """Tests the GetRecipes function."""
    test_manager = manager.RecipesManager()

    test_recipe = TestRecipe()

    test_manager.RegisterRecipe(test_recipe)

    registered_recipes = test_manager.GetRecipes()
    self.assertEqual(registered_recipes, [test_recipe])

    test_manager.DeregisterRecipe(test_recipe)

  def testRegisterRecipes(self):
    """Tests the RegisterRecipes function."""
    test_manager = manager.RecipesManager()

    test_recipe = TestRecipe()

    number_of_recipes = len(test_manager._recipes)

    test_manager.RegisterRecipes([test_recipe])
    self.assertEqual(len(test_manager._recipes), number_of_recipes + 1)

    test_manager.DeregisterRecipe(test_recipe)


if __name__ == '__main__':
  unittest.main()
