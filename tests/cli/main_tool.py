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
    dftimewolf_recipes.SetupLogging()
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
    # We want to access the tool's sate object to load recipes and go through
    # modules.
    # pylint: disable=protected-access
    self.tool._state =  dftw_state.DFTimewolfState(config.Config)

    for recipe in self.tool._recipes_manager.GetRecipes():
      self.tool._state.LoadRecipe(recipe.contents, dftimewolf_recipes.MODULES)
      modules = recipe.contents['modules']
      preflights = recipe.contents.get('preflights', [])
      for module in modules + preflights:
        runtime_name = module.get('runtime_name', module['name'])
        setup_func = self.tool.state._module_pool[runtime_name].SetUp
        expected_args = set(inspect.getfullargspec(setup_func).args)
        expected_args.remove('self')
        provided_args = set(module['args'])

        self.assertEqual(
          expected_args,
          provided_args,
          f'Error in {recipe.name}:{runtime_name}')
