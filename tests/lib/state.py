#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests State."""

from __future__ import unicode_literals

import unittest

import mock

from dftimewolf import config
from dftimewolf.lib import containers
from dftimewolf.lib import resources
from dftimewolf.lib import state
from dftimewolf.lib.errors import DFTimewolfError
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.recipes import manager as recipes_manager

from tests.test_modules import modules, test_recipe


class StateTest(unittest.TestCase):
  """Tests for the DFTimewolfState class."""

  def setUp(self):
    """Registers the dummy modules and recipe to be used in tests."""
    modules_manager.ModulesManager.RegisterModules([
        modules.DummyModule1, modules.DummyModule2])

    self._recipe = resources.Recipe(
        test_recipe.__doc__, test_recipe.contents, test_recipe.args)
    recipes_manager.RecipesManager.RegisterRecipe(self._recipe)

  def tearDown(self):
    """Deregister the recipe used in tests."""
    recipes_manager.RecipesManager.DeregisterRecipe(self._recipe)

    modules_manager.ModulesManager.DeregisterModule(modules.DummyModule1)
    modules_manager.ModulesManager.DeregisterModule(modules.DummyModule2)

  def testLoadRecipe(self):
    """Tests that a recipe can be loaded correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.load_recipe(test_recipe.contents)
    # pylint: disable=protected-access
    self.assertIn('DummyModule1', test_state._module_pool)
    self.assertIn('DummyModule2', test_state._module_pool)
    self.assertEqual(len(test_state._module_pool), 2)

  def testStoreContainer(self):
    """Tests that containers are stored correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.store_container(
        containers.Report(module_name='foo', text='bar'))
    self.assertEqual(len(test_state.store), 1)
    self.assertIn('report', test_state.store)
    self.assertEqual(len(test_state.store['report']), 1)
    self.assertIsInstance(test_state.store['report'][0], containers.Report)

  def testGetContainer(self):
    """Tests that containers can be retrieved."""
    test_state = state.DFTimewolfState(config.Config)
    dummy_report = containers.Report(module_name='foo', text='bar')
    test_state.store_container(dummy_report)
    reports = test_state.get_containers(containers.Report)
    self.assertEqual(len(reports), 1)
    self.assertIsInstance(reports[0], containers.Report)

  @mock.patch('tests.test_modules.modules.DummyModule2.setup')
  @mock.patch('tests.test_modules.modules.DummyModule1.setup')
  def testSetupModules(self, mock_setup1, mock_setup2):
    """Tests that module's setup functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.load_recipe(test_recipe.contents)
    test_state.setup_modules(DummyArgs())
    mock_setup1.assert_called_with()
    mock_setup2.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyModule2.Process')
  @mock.patch('tests.test_modules.modules.DummyModule1.Process')
  def testProcessModules(self, mock_process1, mock_process2):
    """Tests that modules' process functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.load_recipe(test_recipe.contents)
    test_state.setup_modules(DummyArgs())
    test_state.run_modules()
    mock_process1.assert_called_with()
    mock_process2.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyModule2.Process')
  @mock.patch('tests.test_modules.modules.DummyModule1.Process')
  @mock.patch('sys.exit')
  def testProcessErrors(self, mock_exit, mock_process1, mock_process2):
    """Tests that module's errors arre correctly caught."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.load_recipe(test_recipe.contents)
    test_state.setup_modules(DummyArgs())
    mock_process1.side_effect = Exception('asd')
    mock_process2.side_effect = DFTimewolfError('dfTimewolf Error')
    test_state.run_modules()
    mock_process1.assert_called_with()
    mock_process2.assert_called_with()
    mock_exit.assert_called_with(-1)
    self.assertEqual(len(test_state.global_errors), 2)
    msg, critical = sorted(test_state.global_errors, key=lambda x: x[0])[0]
    self.assertIn('An unknown error occurred: asd', msg)
    self.assertTrue(critical)
    msg, critical = sorted(test_state.global_errors, key=lambda x: x[0])[1]
    self.assertIn('dfTimewolf Error', msg)
    self.assertTrue(critical)


# pylint: disable=no-init,unnecessary-pass
class DummyArgs:
  """Fake class to generate an object with an empty __dict__ attribute."""
  pass

if __name__ == '__main__':
  unittest.main()
