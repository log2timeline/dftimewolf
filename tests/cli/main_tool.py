#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the main tool functionality."""

import logging
import inspect

from absl.testing import absltest
from absl.testing import parameterized

from dftimewolf.cli import dftimewolf_recipes
from dftimewolf.lib import state as dftw_state
from dftimewolf.lib import resources, errors
from dftimewolf.lib.validators import manager as validators_manager

# The following import makes sure validators are registered.
from dftimewolf.lib import validators # pylint: disable=unused-import

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

OPTIONAL_ARG_RECIPE = {
    'name': 'optional_arg_recipe',
    'short_description': 'Short description.',
    'preflights': [],
    'modules': [],
    'args': [
        ['mandatory_arg', 'Mandatory Argument', None],
        ['--optional_arg', 'Optional Argument', None,
            {'format': 'regex', 'regex': '^Second$'}]
    ]
}

OPTIONAL_ARG_RECIPE_ARGS = [
    resources.RecipeArgument(*arg) for arg in OPTIONAL_ARG_RECIPE['args']]


def _CreateToolObject():
  """Creates a DFTimewolfTool object instance."""
  tool = dftimewolf_recipes.DFTimewolfTool()
  tool.LoadConfiguration()
  try:
    tool.ReadRecipes()
  except KeyError:
    # Prevent conflicts from other tests where recipes are still registered.
    pass
  return tool


def _EnumerateRecipeNames():
  """Enumerate recipe names for the purposes of generatting parameterised tests.
  """
  tool = _CreateToolObject()
  # pylint: disable=protected-access
  for recipe in tool._recipes_manager.GetRecipes():
    yield (f'_{recipe.name}', recipe.name)


class MainToolTest(parameterized.TestCase):
  """Tests for main tool functions."""

  def setUp(self):
    self.tool = _CreateToolObject()

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

  @parameterized.named_parameters(_EnumerateRecipeNames())
  def testRecipeSetupArgs(self, recipe_name):
    """Parameterised version of _testRecipeSetupArgs."""
    self._testRecipeSetupArgs(recipe_name)

  def _testRecipeSetupArgs(self, recipe_name):
    """Checks that all recipes pass the correct arguments to their modules."""
    # We want to access the tool's state object to load recipes and go through
    # modules.
    # pylint: disable=protected-access
    self.tool._state = dftw_state.DFTimewolfState(config.Config)
    recipe = self.tool._recipes_manager.Recipes()[recipe_name]

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

  @parameterized.named_parameters(_EnumerateRecipeNames())
  def testRecipeValidators(self, recipe_name):
    """Parameterised version of _testRecipeValidators."""
    self._testRecipeValidators(recipe_name)

  def _testRecipeValidators(self, recipe_name):
    """Tests that recipes do not specify invalid validators."""
    # pylint: disable=protected-access
    self.tool._state = dftw_state.DFTimewolfState(config.Config)
    recipe = self.tool._recipes_manager.Recipes()[recipe_name]

    test_params = recipe.GetTestParams()
    if test_params:
      recipe_args = [recipe_name] + test_params
      self.tool.ParseArguments(recipe_args)
    else:
      self.fail('No test_params in recipe')

    self.tool._state.LoadRecipe(recipe.contents, dftimewolf_recipes.MODULES)
    for arg in recipe.args:
      if arg.validation_params:
        self.assertIn(
            arg.validation_params['format'],
            validators_manager.ValidatorsManager.ListValidators(),
            f'Error in {recipe.name}:{arg.switch} - '
            f'Invalid validator {arg.validation_params["format"]}.')

    self.tool.ValidateArguments()

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
        errors.CriticalError, 'At least one argument failed validation'):
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

  def testOptionalArguments(self):
    """Tests handling of optional arguments."""
    # pylint: disable=protected-access
    optional_arg_recipe = resources.Recipe(
        OPTIONAL_ARG_RECIPE.__doc__,
        OPTIONAL_ARG_RECIPE,
        OPTIONAL_ARG_RECIPE_ARGS)
    self.tool._state = dftw_state.DFTimewolfState(config.Config)
    self.tool._recipes_manager.RegisterRecipe(optional_arg_recipe)
    self.tool._state.LoadRecipe(OPTIONAL_ARG_RECIPE, dftimewolf_recipes.MODULES)

    self.tool.ParseArguments(['optional_arg_recipe', 'First'])
    self.tool.ValidateArguments() # No value for optional arg is ok.

    self.tool.ParseArguments([
        'optional_arg_recipe', 'First', '--optional_arg', 'Second'])
    self.tool.ValidateArguments() # Valid value for optional arg is ok.

    # Invalid value for optional arg is not ok.
    self.tool.ParseArguments([
        'optional_arg_recipe', 'First', '--optional_arg', 'not_second'])
    with self.assertRaises(errors.CriticalError):
      self.tool.ValidateArguments()


if __name__ == '__main__':
  absltest.main()
