#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests State."""

import unittest

import mock

from dftimewolf import config
from dftimewolf.lib import resources
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.errors import DFTimewolfError
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.recipes import manager as recipes_manager

from tests.test_modules import modules
from tests.test_modules import test_recipe


class StateTest(unittest.TestCase):
  """Tests for the DFTimewolfState class."""

  def setUp(self):
    """Registers the dummy modules and recipe to be used in tests."""
    modules_manager.ModulesManager.RegisterModules([
        modules.DummyModule1, modules.DummyModule2,
        modules.DummyPreflightModule])

    self._recipe = resources.Recipe(
        test_recipe.__doc__, test_recipe.contents, test_recipe.args)
    self._recipes_manager = recipes_manager.RecipesManager()
    self._recipes_manager.RegisterRecipe(self._recipe)

  def tearDown(self):
    """Deregister the recipe used in tests."""
    self._recipes_manager.DeregisterRecipe(self._recipe)

    modules_manager.ModulesManager.DeregisterModule(modules.DummyModule1)
    modules_manager.ModulesManager.DeregisterModule(modules.DummyModule2)
    modules_manager.ModulesManager.DeregisterModule(
        modules.DummyPreflightModule)

  def testLoadRecipe(self):
    """Tests that a recipe can be loaded correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.LoadRecipe(test_recipe.contents)
    # pylint: disable=protected-access
    self.assertIn('DummyModule1', test_state._module_pool)
    self.assertIn('DummyModule2', test_state._module_pool)
    self.assertIn('DummyPreflightModule', test_state._module_pool)
    self.assertEqual(len(test_state._module_pool), 3)

  def testStoreContainer(self):
    """Tests that containers are stored correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_report = containers.Report(module_name='foo', text='bar')
    test_state.StoreContainer(test_report)
    self.assertEqual(len(test_state.store), 1)
    self.assertIn('report', test_state.store)
    self.assertEqual(len(test_state.store['report']), 1)
    self.assertIsInstance(test_state.store['report'][0], containers.Report)

  def testGetContainer(self):
    """Tests that containers can be retrieved."""
    test_state = state.DFTimewolfState(config.Config)
    test_report = containers.Report(module_name='foo', text='bar')
    test_state.StoreContainer(test_report)
    reports = test_state.GetContainers(containers.Report)
    self.assertEqual(len(reports), 1)
    self.assertIsInstance(reports[0], containers.Report)

  @mock.patch('tests.test_modules.modules.DummyPreflightModule.Process')
  @mock.patch('tests.test_modules.modules.DummyPreflightModule.SetUp')
  def testProcessPreflightModules(self, mock_setup, mock_process):
    """Tests that preflight's process function is called correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.contents)
    test_state.RunPreflights()
    mock_setup.assert_called_with()
    mock_process.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyModule2.SetUp')
  @mock.patch('tests.test_modules.modules.DummyModule1.SetUp')
  def testSetupModules(self, mock_setup1, mock_setup2):
    """Tests that module's setup functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.contents)
    test_state.SetupModules()
    mock_setup1.assert_called_with()
    mock_setup2.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyModule2.Process')
  @mock.patch('tests.test_modules.modules.DummyModule1.Process')
  def testProcessModules(self, mock_process1, mock_process2):
    """Tests that modules' process functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.contents)
    test_state.SetupModules()
    test_state.RunModules()
    mock_process1.assert_called_with()
    mock_process2.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyModule2.Process')
  @mock.patch('tests.test_modules.modules.DummyModule1.Process')
  @mock.patch('sys.exit')
  def testProcessErrors(self, mock_exit, mock_process1, mock_process2):
    """Tests that module's errors are correctly caught."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.contents)
    mock_process1.side_effect = Exception('asd')
    mock_process2.side_effect = DFTimewolfError('dfTimewolf Error')
    test_state.SetupModules()
    test_state.RunModules()
    mock_process1.assert_called_with()
    mock_process2.assert_called_with()
    mock_exit.assert_called_with(1)
    self.assertEqual(len(test_state.global_errors), 2)
    msg, critical = sorted(test_state.global_errors, key=lambda x: x[0])[0]
    self.assertIn('An unknown error occurred: asd', msg)
    self.assertTrue(critical)
    msg, critical = sorted(test_state.global_errors, key=lambda x: x[0])[1]
    self.assertIn('dfTimewolf Error', msg)
    self.assertTrue(critical)

  @mock.patch('tests.test_modules.modules.DummyModule1.Callback')
  def testStreamingCallback(self, mock_callback):
    """Tests that registered callbacks are appropriately called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.LoadRecipe(test_recipe.contents)
    test_state.SetupModules()
    # DummyModule1 has registered a StreamingConsumer
    report = containers.Report(module_name='testing', text='asd')
    test_state.StreamContainer(report)
    mock_callback.assert_called_with(report)

  @mock.patch('tests.test_modules.modules.DummyModule1.Callback')
  def testStreamingCallbackNotCalled(self, mock_callback):
    """Tests that registered callbacks are called only on types for which
    they are registered."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.LoadRecipe(test_recipe.contents)
    test_state.SetupModules()
    # DummyModule1's registered StreamingConsumer only consumes Reports, not
    # TicketAtttributes
    attributes = containers.TicketAttribute(
        type_='asd', name='asd', value='asd')
    test_state.StreamContainer(attributes)
    mock_callback.assert_not_called()

if __name__ == '__main__':
  unittest.main()
