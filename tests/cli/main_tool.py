#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the main tool functionality."""

import unittest
import logging

from dftimewolf.cli import dftimewolf_recipes


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
