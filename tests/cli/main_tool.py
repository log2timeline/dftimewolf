#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the main tool functionality."""

import unittest
import logging
import inspect

from dftimewolf.cli import dftimewolf_recipes
from dftimewolf.lib import state as dftw_state
from dftimewolf.lib import resources, errors, args_validator
from dftimewolf import config

# This test recipe requires two args: Anything for arg1, and the word 'Second'
# for arg2. The value for arg1 will be substituted into 'other_arg' in arg2.
NESTED_ARG_RECIPE = {
    'name': 'nested_arg_recipe',
    'short_description': 'Short description.',
    'preflights': [],
    'modules': [],
    'args': [
      ['arg1', 'Argument 1', None],
      ['arg2', 'Argument 2', None,  {'format': 'regex',
                                     'regex': '^Second$',
                                     'other_arg': '@arg1'}]
    ]
}

NESTED_ARG_RECIPE_ARGS = [
    resources.RecipeArgument(*arg) for arg in NESTED_ARG_RECIPE['args']]

class MainToolTest(unittest.TestCase):
  """Tests for main tool functions."""

  def setUp(self):
    self.tool = dftimewolf_recipes.DFTimewolfTool()
    self.tool.LoadConfiguration()
    try:
      self.tool.ReadRecipes()
    except KeyError:
      # Prevent conflicts from other tests where recipes are still registered.
      pass

  def tearDown(self):
    # pylint: disable=protected-access
    for recipe in self.tool._recipes_manager.GetRecipes():
      self.tool._recipes_manager.DeregisterRecipe(recipe)

  def testSetupLogging(self):
    """Tests the SetupLogging function."""
    dftimewolf_recipes.SetupLogging(True)
    logger = logging.getLogger('dftimewolf')
    root_logger = logging.getLogger()
    self.assertEqual(len(logger.handlers), 2)
    self.assertEqual(len(root_logger.handlers), 1)

  def testToolWithArbitraryRecipe(self):
    """Tests that recipes are read and valid, and an exec plan is logged."""
    # We want to ensure that recipes are loaded (10 is arbitrary)
    # pylint: disable=protected-access
    self.assertGreater(len(self.tool._recipes_manager._recipes), 10)
    # Conversion to parse arguments is done within ParseArguments
    # We can pass an arbitrary recipe with valid args here.
    self.tool.ParseArguments(['upload_ts', '/tmp/test'])
    self.tool.state.LogExecutionPlan()

  def testRecipeSetupArgs(self):
    """Checks that all recipes pass the correct arguments to their modules."""
    # We want to access the tool's state object to load recipes and go through
    # modules.
    # pylint: disable=protected-access
    self.tool._state = dftw_state.DFTimewolfState(config.Config)

    for recipe in self.tool._recipes_manager.GetRecipes():
      self.tool._state.LoadRecipe(recipe.contents, dftimewolf_recipes.MODULES)
      modules = recipe.contents['modules']
      preflights = recipe.contents.get('preflights', [])
      for module in modules + preflights:
        runtime_name = module.get('runtime_name', module['name'])
        if runtime_name in self.tool.state._module_pool:
          setup_func = self.tool.state._module_pool[runtime_name].SetUp
          expected_args = set(inspect.getfullargspec(setup_func).args)
          expected_args.remove('self')
          provided_args = set(module['args'])

          self.assertEqual(
            expected_args,
            provided_args,
            f'Error in {recipe.name}:{runtime_name}')

  def testRecipeValidators(self):
    """Tests that recipes do not specify invalid validators."""
    # pylint: disable=protected-access
    self.tool._state = dftw_state.DFTimewolfState(config.Config)

    for recipe in self.tool._recipes_manager.GetRecipes():
      self.tool._state.LoadRecipe(recipe.contents, dftimewolf_recipes.MODULES)
      for arg in recipe.args:
        if arg.validation_params:
          self.assertIn(
              arg.validation_params['format'],
              args_validator.ValidatorsManager.ListValidators(),
              f'Error in {recipe.name}:{arg.switch} - '
              f'Invalid validator {arg.validation_params["format"]}.')

  def testRecipeWithNestedArgs(self):
    """Tests that a recipe with args referenced in other args is populated."""
    # pylint: disable=protected-access
    nested_arg_recipe = resources.Recipe(
        NESTED_ARG_RECIPE.__doc__,
        NESTED_ARG_RECIPE,
        NESTED_ARG_RECIPE_ARGS)
    self.tool._state = dftw_state.DFTimewolfState(config.Config)
    self.tool._recipes_manager.RegisterRecipe(nested_arg_recipe)
    self.tool._state.LoadRecipe(NESTED_ARG_RECIPE, dftimewolf_recipes.MODULES)

    self.tool.ParseArguments(['nested_arg_recipe', 'First', 'Second'])
    self.tool.ValidateArguments()

    # Check the nested arg 'First' has been inserted into the 'other_arg' value
    # of 'arg2'
    for arg in NESTED_ARG_RECIPE_ARGS:
      if arg.switch == 'arg2':
        self.assertEqual(arg.validation_params['other_arg'], 'First')

  def testFailingArgValidation(self):
    """Tests that a recipe fails when args don't validate."""
    # pylint: disable=protected-access
    nested_arg_recipe = resources.Recipe(
        NESTED_ARG_RECIPE.__doc__,
        NESTED_ARG_RECIPE,
        NESTED_ARG_RECIPE_ARGS)
    self.tool._state = dftw_state.DFTimewolfState(config.Config)
    self.tool._recipes_manager.RegisterRecipe(nested_arg_recipe)
    self.tool._state.LoadRecipe(NESTED_ARG_RECIPE, dftimewolf_recipes.MODULES)

    self.tool.ParseArguments(['nested_arg_recipe', 'First', 'Not Second'])

    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        'At least one argument failed validation'):
      self.tool.ValidateArguments()

  def testDryRun(self):
    """Tests setting the dry_run flag."""
    # pylint: disable=protected-access
    nested_arg_recipe = resources.Recipe(
        NESTED_ARG_RECIPE.__doc__,
        NESTED_ARG_RECIPE,
        NESTED_ARG_RECIPE_ARGS)
    self.tool._state = dftw_state.DFTimewolfState(config.Config)
    self.tool._recipes_manager.RegisterRecipe(nested_arg_recipe)
    self.tool._state.LoadRecipe(NESTED_ARG_RECIPE, dftimewolf_recipes.MODULES)

    self.tool.ParseArguments(
        ['--dry_run', 'nested_arg_recipe', 'First', 'Not Second'])

    self.assertTrue(self.tool.dry_run)


if __name__ == '__main__':
  unittest.main()
