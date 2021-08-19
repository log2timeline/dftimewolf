#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests State."""

import unittest

import mock

from dftimewolf import config
from dftimewolf.lib import resources
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.recipes import manager as recipes_manager
from dftimewolf.lib import errors

from tests.test_modules import modules
from tests.test_modules import thread_aware_modules
from tests.test_modules import test_recipe

TEST_MODULES = {
  'DummyModule1': 'tests.test_modules.modules',
  'DummyModule2': 'tests.test_modules.modules',
  'DummyPreflightModule': 'tests.test_modules.modules',
  'ContainerGeneratorModule': 'tests.test_modules.thread_aware_modules',
  'ThreadAwareConsumerModule': 'tests.test_modules.thread_aware_modules'
}

class StateTest(unittest.TestCase):
  """Tests for the DFTimewolfState class."""

  def setUp(self):
    """Registers the dummy modules and recipe to be used in tests."""
    modules_manager.ModulesManager.RegisterModules([
        modules.DummyModule1,
        modules.DummyModule2,
        modules.DummyPreflightModule,
        thread_aware_modules.ContainerGeneratorModule,
        thread_aware_modules.ThreadAwareConsumerModule])

    self._recipe = resources.Recipe(
        test_recipe.__doc__, test_recipe.contents, test_recipe.args)
    self._threaded_recipe = resources.Recipe(
        test_recipe.__doc__,
        test_recipe.threaded_no_preflights,
        test_recipe.args)
    self._recipes_manager = recipes_manager.RecipesManager()
    self._recipes_manager.RegisterRecipe(self._recipe)
    self._recipes_manager.RegisterRecipe(self._threaded_recipe)

  def tearDown(self):
    """Deregister the recipe used in tests."""
    self._recipes_manager.DeregisterRecipe(self._recipe)
    self._recipes_manager.DeregisterRecipe(self._threaded_recipe)

    modules_manager.ModulesManager.DeregisterModule(modules.DummyModule1)
    modules_manager.ModulesManager.DeregisterModule(modules.DummyModule2)
    modules_manager.ModulesManager.DeregisterModule(
        modules.DummyPreflightModule)
    modules_manager.ModulesManager.DeregisterModule(
        thread_aware_modules.ContainerGeneratorModule)
    modules_manager.ModulesManager.DeregisterModule(
        thread_aware_modules.ThreadAwareConsumerModule)

  def testLoadRecipe(self):
    """Tests that a recipe can be loaded correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)
    # pylint: disable=protected-access
    self.assertIn('DummyModule1', test_state._module_pool)
    self.assertIn('DummyModule2', test_state._module_pool)
    self.assertIn('DummyPreflightModule', test_state._module_pool)
    self.assertEqual(len(test_state._module_pool), 3)

  def testLoadRecipeNoPreflights(self):
    """Tests that a recipe can be loaded correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.LoadRecipe(test_recipe.contents_no_preflights, TEST_MODULES)
    # pylint: disable=protected-access
    self.assertIn('DummyModule1', test_state._module_pool)
    self.assertIn('DummyModule2', test_state._module_pool)
    self.assertEqual(len(test_state._module_pool), 2)

  def testLoadRecipeThreadAwareModule(self):
    """Tests that a recipe can be loaded correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.LoadRecipe(test_recipe.threaded_no_preflights, TEST_MODULES)
    # pylint: disable=protected-access
    self.assertIn('ContainerGeneratorModule', test_state._module_pool)
    self.assertIn('ThreadAwareConsumerModule', test_state._module_pool)
    self.assertEqual(len(test_state._module_pool), 2)

  def testLoadRecipeWithRuntimeNames(self):
    """Tests that a recipe can be loaded correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.LoadRecipe(test_recipe.named_modules_contents, TEST_MODULES)
    # pylint: disable=protected-access
    self.assertIn('DummyModule1', test_state._module_pool)
    self.assertIn('DummyModule2', test_state._module_pool)
    self.assertIn('DummyModule1-2', test_state._module_pool)
    self.assertIn('DummyModule2-2', test_state._module_pool)
    self.assertIn('DummyPreflightModule-runtime', test_state._module_pool)
    self.assertEqual(len(test_state._module_pool), 5)

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
    test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)
    test_state.RunPreflights()
    mock_setup.assert_called_with()
    mock_process.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyPreflightModule.Process')
  @mock.patch('tests.test_modules.modules.DummyPreflightModule.SetUp')
  def testProcessNamedPreflightModules(self, mock_setup, mock_process):
    """Tests that preflight's process function is called correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.named_modules_contents, TEST_MODULES)
    test_state.RunPreflights()
    mock_setup.assert_called_with()
    mock_process.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyPreflightModule.CleanUp')
  def testCleanupPreflightModules(self, mock_cleanup):
    """Tests that preflight's process function is called correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)
    test_state.CleanUpPreflights()
    mock_cleanup.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyModule2.SetUp')
  @mock.patch('tests.test_modules.modules.DummyModule1.SetUp')
  def testSetupModules(self, mock_setup1, mock_setup2):
    """Tests that module's setup functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)
    test_state.SetupModules()
    mock_setup1.assert_called_with()
    mock_setup2.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyModule2.SetUp')
  @mock.patch('tests.test_modules.modules.DummyModule1.SetUp')
  def testSetupNamedModules(self, mock_setup1, mock_setup2):
    """Tests that module's setup functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.named_modules_contents, TEST_MODULES)
    test_state.SetupModules()
    self.assertEqual(
      mock_setup1.call_args_list,
      [mock.call(runtime_value='1-1'), mock.call(runtime_value='1-2')])
    self.assertEqual(
      mock_setup2.call_args_list,
      [mock.call(runtime_value='2-1'), mock.call(runtime_value='2-2')])

  # pylint: disable=line-too-long
  @mock.patch('tests.test_modules.thread_aware_modules.ContainerGeneratorModule.SetUp')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.SetUp')
  # pylint: enable=line-too-long
  def testSetupThreadModules(self, mock_threaded_setup, mock_dummy_setup):
    """Tests that threaded module's setup functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.threaded_no_preflights, TEST_MODULES)
    test_state.SetupModules()
    self.assertEqual(
      mock_dummy_setup.call_args_list,
      [mock.call(runtime_value='one,two,three')])
    self.assertEqual(
      mock_threaded_setup.call_args_list,
      [mock.call()])

  @mock.patch('tests.test_modules.modules.DummyModule2.Process')
  @mock.patch('tests.test_modules.modules.DummyModule1.Process')
  def testProcessModules(self, mock_process1, mock_process2):
    """Tests that modules' process functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)
    test_state.SetupModules()
    test_state.RunModules()
    mock_process1.assert_called_with()
    mock_process2.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyModule2.Process')
  @mock.patch('tests.test_modules.modules.DummyModule1.Process')
  def testProcessNamedModules(self, mock_process1, mock_process2):
    """Tests that modules' process functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.named_modules_contents, TEST_MODULES)
    test_state.SetupModules()
    test_state.RunModules()
    # pylint: disable=protected-access
    self.assertIn('DummyModule1', test_state._threading_event_per_module)
    self.assertIn('DummyModule2', test_state._threading_event_per_module)
    self.assertIn('DummyModule1-2', test_state._threading_event_per_module)
    self.assertIn('DummyModule2-2', test_state._threading_event_per_module)
    self.assertEqual(mock_process1.call_count, 2)
    self.assertEqual(mock_process2.call_count, 2)

  # pylint: disable=line-too-long
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.Process')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.StaticPreSetUp')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.StaticPostSetUp')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.StaticPreProcess')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.StaticPostProcess')
  # pylint: enable=line-too-long
  def testProcessThreadAwareModule(self,
      mock_static_post_process,
      mock_static_pre_process,
      mock_static_post_setup,
      mock_static_pre_setup,
      mock_threaded_process):
    """Tests the ThreadAwareModules process functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.threaded_no_preflights, TEST_MODULES)
    test_state.SetupModules()
    test_state.RunModules()
    self.assertEqual(mock_threaded_process.call_count, 3)
    self.assertEqual(mock_static_post_process.call_count, 1)
    self.assertEqual(mock_static_pre_process.call_count, 1)
    self.assertEqual(mock_static_post_setup.call_count, 1)
    self.assertEqual(mock_static_pre_setup.call_count, 1)
    self.assertEqual(3,
        len(test_state.GetContainers(thread_aware_modules.TestContainer)))

  def testThreadAwareModuleContainerHandling(self):
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.threaded_no_preflights, TEST_MODULES)
    test_state.SetupModules()
    test_state.RunModules()

    # With no mocks, the first module generates 3 TestContainers, and 1
    # TestContainerTwo. The Test ThreadAwareConsumerModule is threaded on
    # and modifies TestContainer, and modifies TestContainerTwo.
    values = [container.value for container in test_state.GetContainers(
        thread_aware_modules.TestContainer)]
    expected_values = ['one appended', 'two appended', 'three appended']

    self.assertEqual(sorted(values), sorted(expected_values))
    self.assertEqual(
        test_state.GetContainers(
            thread_aware_modules.TestContainerTwo)[0].value,
        'one,two,three appended appended appended'
        )

  @mock.patch('tests.test_modules.modules.DummyModule2.Process')
  @mock.patch('tests.test_modules.modules.DummyModule1.Process')
  def testProcessErrors(self, mock_process1, mock_process2):
    """Tests that module's errors are correctly caught."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)
    mock_process1.side_effect = Exception('asd')
    test_state.SetupModules()
    with self.assertRaises(errors.CriticalError):
      test_state.RunModules()
    mock_process1.assert_called_with()
    # Process() in module 2 is never called since the failure in Module1
    # will abort execution
    mock_process2.assert_not_called()
    self.assertEqual(len(test_state.global_errors), 1)
    error = test_state.global_errors[0]
    self.assertIn('An unknown error occurred in module DummyModule1: asd',
                  error.message)
    self.assertTrue(error.critical)

  @mock.patch('tests.test_modules.modules.DummyModule1.Callback')
  def testStreamingCallback(self, mock_callback):
    """Tests that registered callbacks are appropriately called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)
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
    test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)
    test_state.SetupModules()
    # DummyModule1's registered StreamingConsumer only consumes Reports, not
    # TicketAtttributes
    attributes = containers.TicketAttribute(
        type_='asd', name='asd', value='asd')
    test_state.StreamContainer(attributes)
    mock_callback.assert_not_called()

if __name__ == '__main__':
  unittest.main()
