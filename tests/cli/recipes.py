#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem collector."""

import os
import unittest

import six

from dftimewolf.lib.recipes import manager as recipes_manager


class RecipeTests(unittest.TestCase):
  """Tests for recipe construction."""

  def setUp(self):
    recipes_path = os.path.dirname(__file__)
    recipes_path = os.path.dirname(recipes_path)
    recipes_path = os.path.dirname(recipes_path)
    recipes_path = os.path.join(recipes_path, 'data', 'recipes')

    self._recipes_manager = recipes_manager.RecipesManager()
    self._recipes_manager.ReadRecipesFromDirectory(recipes_path)

  def tearDown(self):
    for recipe in self._recipes_manager.GetRecipes():
      self._recipes_manager.DeregisterRecipe(recipe)

  def testRecipeHasFields(self):
    """Tests that all recipes have the correct fields."""
    for recipe in self._recipes_manager.GetRecipes():
      self.assertIsNotNone(recipe.name)
      self.assertIsNotNone(recipe.description)
      self.assertIn('modules', recipe.contents)
      self.assertIsInstance(recipe.contents['modules'], list)

      self.assertIsInstance(recipe.args, list)

  def testRecipeModulesHaveFields(self):
    """Tests that modules defined in the recipe have the correct fields."""
    for recipe in self._recipes_manager.GetRecipes():
      for module in recipe.contents['modules']:
        error_msg = 'module {0:s} in recipe {1:s}'.format(
            module['name'], recipe.contents['name'])

        self.assertIn('wants', module, msg=error_msg)
        self.assertIn('name', module, msg=error_msg)
        self.assertIn('args', module, msg=error_msg)

        self.assertIsInstance(module['wants'], list, msg=error_msg)
        self.assertIsInstance(module['args'], dict, msg=error_msg)
        self.assertIsInstance(module['name'], six.string_types, msg=error_msg)

  def testRecipeModulesAllPresent(self):
    """Tests that a recipe's modules depend only on modules present in the
    recipe."""
    for recipe in self._recipes_manager.GetRecipes():
      declared_modules = set()
      wanted_modules = set()
      for module in recipe.contents['modules']:

        declared_modules.add(module['name'])
        for wanted in module['wants']:
          wanted_modules.add(wanted)

      for wanted_module in wanted_modules:
        self.assertIn(wanted_module, declared_modules,
                      msg='recipe: {0:s}'.format(recipe.contents['name']))

  def testNoDeadlockInRecipe(self):
    """Tests that a recipe will not deadlock."""
    for recipe in self._recipes_manager.GetRecipes():
      for module in recipe.contents['modules']:
        dependencies = _FindModuleDependencies(
            module['name'], recipe, module['name'])
        if module['name'] in dependencies:
          self.fail('Cyclic dependency found in {0:s}: {1:s}'.format(
              recipe.contents['name'],
              module['name']
          ))


def _FindModuleDependencies(module_name, recipe, original_module_name):
  """Recursively looks for module dependencies.

  Will stop whenever the original module is found to be a dependency of itself,
  or when all dependencies are found.

  Args:
    module_name (str): name of the module to check dependencies for
    recipe (str): name of the dftimewolf recipe
    original_module_name (str): original module name for which we want to check
        for cyclic dependencies.

  Returns:
    set[str]: depencency names found.
  """
  module_dependencies = set()
  for module in recipe.contents['modules']:
    if module_name == module['name']:
      module_dependencies.update(module['wants'])

  if original_module_name in module_dependencies:
    # We found a cyclic dependency, stop recursing and return immediately.
    return module_dependencies

  # otherwise, check for another level of dependencies.
  for dependency in list(module_dependencies):
    module_dependencies.update(_FindModuleDependencies(
        dependency, recipe, original_module_name))

  return module_dependencies



if __name__ == '__main__':
  unittest.main()
