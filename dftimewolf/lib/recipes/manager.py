# -*- coding: utf-8 -*-
"""Recipes manager."""

import io
import glob
import json
import os

from dftimewolf.lib import errors
from dftimewolf.lib import resources


class RecipesManager(object):
  """Recipes manager."""

  # Allow a previously registered recipe to be overridden.
  ALLOW_RECIPE_OVERRIDE = False

  _recipes = {}

  def _ReadRecipeFromFileObject(self, file_object):
    """Reads a recipe from a JSON file-like object.

    Args:
      file_object (file): JSON file-like object that contains the recipe.

    Returns:
      Recipe: recipe.
    """
    json_dict = json.load(file_object)

    description = json_dict['description']
    del json_dict['description']

    args = json_dict['args']
    del json_dict['args']

    return resources.Recipe(description, json_dict, args)

  def DeregisterRecipe(self, recipe):
    """Deregisters a recipe.

    The recipe are identified based on their lower case name.

    Args:
      recipe (Recipe): the recipe.

    Raises:
      KeyError: if recipe is not set for the corresponding name.
    """
    recipe_name = recipe.name.lower()
    if recipe_name not in self._recipes:
      raise KeyError('Recipe not set for name: {0:s}.'.format(recipe.name))

    del self._recipes[recipe_name]

  def GetRecipes(self):
    """Retrieves the registered recipes.

    Returns:
      list[Recipe]: the recipes sorted by name.
    """
    return sorted(self._recipes.values(), key=lambda recipe: recipe.name)

  def ReadRecipeFromFile(self, path):
    """Reads a recipe from a JSON file.

    Args:
      path (str): path of the recipe JSON file.

    Raises:
      RecipeParseError: when the recipe cannot be parsed.
    """
    with io.open(path, 'r', encoding='utf-8') as file_object:
      try:
        recipe = self._ReadRecipeFromFileObject(file_object)
      except json.decoder.JSONDecodeError as exception:
        raise errors.RecipeParseError(
            'Unable to parse recipe file: {0:s} with error: {1!s}'.format(
                path, exception))

    self.RegisterRecipe(recipe)

  def ReadRecipesFromDirectory(self, path):
    """Reads recipes from a directory containing JSON files.

    Args:
      path (str): path of the directory containing the recipes JSON files.
    """
    for file_path in glob.glob(os.path.join(path, '*.json')):
      self.ReadRecipeFromFile(file_path)

  def RegisterRecipe(self, recipe):
    """Registers a recipe.

    The recipe are identified based on their lower case name.

    Args:
      recipe (Recipe): the recipe.

    Raises:
      KeyError: if recipe is already set for the corresponding name.
    """
    recipe_name = recipe.name.lower()
    if recipe_name in self._recipes and not self.ALLOW_RECIPE_OVERRIDE:
      raise KeyError('Recipe already set for name: {0:s}.'.format(recipe.name))

    self._recipes[recipe_name] = recipe

  def RegisterRecipes(self, recipes):
    """Registers recipes.

    The recipes are identified based on their lower case name.

    Args:
      recipes (list[Recipe]): the recipes.

    Raises:
      KeyError: if a recipe is already set for the corresponding name.
    """
    for recipe in recipes:
      self.RegisterRecipe(recipe)
