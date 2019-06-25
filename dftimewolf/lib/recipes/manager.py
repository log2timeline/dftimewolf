# -*- coding: utf-8 -*-
"""Recipes manager."""

from __future__ import unicode_literals


class RecipesManager(object):
  """Recipes manager."""

  _recipes = {}

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
