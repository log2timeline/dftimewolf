#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the main tool functionality."""

import unittest
import logging
import inspect

from dftimewolf.cli import dftimewolf_recipes
from dftimewolf.lib import state as dftw_state
from dftimewolf import config

class MainToolTest(unittest.TestCase):
  """Tests for main tool functions."""

  def setUp(self):
    pass

  def testSetupLogging(self):
    """Tests the SetupLogging function."""
    dftimewolf_recipes.SetupLogging()
    logger = logging.getLogger('dftimewolf')
    root_logger = logging.getLogger()
    self.assertEqual(len(logger.handlers), 2)
    self.assertEqual(len(root_logger.handlers), 1)

  def testToolWithArbitraryRecipe(self):
    """Tests that recipes are read and valid, and an exec plan is logged."""
    tool = dftimewolf_recipes.DFTimewolfTool()
    tool.LoadConfiguration()
    tool.ReadRecipes()
    # We want to ensure that recipes are loaded (10 is arbitrary)
    # pylint: disable=protected-access
    self.assertGreater(len(tool._recipes_manager._recipes), 10)
    # Conversion to parse arguments is done within ParseArguments
    # We can pass an arbitrary recipe with valid args here.
    tool.ParseArguments(['upload_ts', '/tmp/test'])
    tool.state.LogExecutionPlan()
    for recipe in tool._recipes_manager.GetRecipes():
      tool._recipes_manager.DeregisterRecipe(recipe)

  def testRecipeSetupArgs(self):
    """Checks that all recipes pass the correct arguments to their modules."""
    tool = dftimewolf_recipes.DFTimewolfTool()
    tool.LoadConfiguration()
    tool.ReadRecipes()

    # We want to access the tool's sate object to load recipes and go through
    # modules.
    # pylint: disable=protected-access
    tool._state =  dftw_state.DFTimewolfState(config.Config)

    for recipe in tool._recipes_manager.GetRecipes():
      tool._state.LoadRecipe(recipe.contents, dftimewolf_recipes.MODULES)
      for module in recipe.contents['modules']:
        runtime_name = module.get('runtime_name', module['name'])
        setup_func = tool.state._module_pool[runtime_name].SetUp
        expected_args = set(inspect.getfullargspec(setup_func).args)
        expected_args.remove('self')
        provided_args = set(module['args'])

        self.assertEqual(
          expected_args,
          provided_args,
          f'Error in {recipe.name}:{runtime_name}')
