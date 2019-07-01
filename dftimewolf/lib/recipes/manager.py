# -*- coding: utf-8 -*-
"""Recipes manager."""

from __future__ import unicode_literals

import io
import json

from dftimewolf.lib import resources


class RecipesManager(object):
  """Recipes manager."""

  _recipes = {}

  @classmethod
  def _ReadRecipeFromFileObject(cls, file_object):
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

  @classmethod
  def DeregisterRecipe(cls, recipe):
    """Deregisters a recipe.

    The recipe are identified based on their lower case name.

    Args:
      recipe (Recipe): the recipe.

    Raises:
      KeyError: if recipe is not set for the corresponding name.
    """
    recipe_name = recipe.name.lower()
    if recipe_name not in cls._recipes:
      raise KeyError('Recipe not set for name: {0:s}.'.format(recipe.name))

    del cls._recipes[recipe_name]

  @classmethod
  def GetRecipes(cls):
    """Retrieves the registered recipes.

    Returns:
      list[Recipe]: the recipes sorted by name.
    """
    return sorted(cls._recipes.values(), key=lambda recipe: recipe.name)

  @classmethod
  def ReadRecipeFromFile(cls, path):
    """Reads a recipe from a JSON file.

    Args:
      path (str): path of the recipe JSON file.
    """
    with io.open(path, 'r', encoding='utf-8') as file_object:
      recipe = cls._ReadRecipeFromFileObject(file_object)

    cls.RegisterRecipe(recipe)

  @classmethod
  def RegisterRecipe(cls, recipe):
    """Registers a recipe.

    The recipe are identified based on their lower case name.

    Args:
      recipe (Recipe): the recipe.

    Raises:
      KeyError: if recipe is already set for the corresponding name.
    """
    recipe_name = recipe.name.lower()
    if recipe_name in cls._recipes:
      raise KeyError('Recipe already set for name: {0:s}.'.format(recipe.name))

    cls._recipes[recipe_name] = recipe

  @classmethod
  def RegisterRecipes(cls, recipes):
    """Registers recipes.

    The recipes are identified based on their lower case name.

    Args:
      recipes (list[Recipe]): the recipes.

    Raises:
      KeyError: if a recipe is already set for the corresponding name.
    """
    for recipe in recipes:
      cls.RegisterRecipe(recipe)
