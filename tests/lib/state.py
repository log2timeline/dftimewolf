#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests State."""

import unittest

import mock

from dftimewolf import config
from dftimewolf.cli.curses_display_manager import CursesDisplayManager, Status
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
  'ThreadAwareConsumerModule': 'tests.test_modules.thread_aware_modules',
  'Issue503Module': 'tests.test_modules.thread_aware_modules'
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
        thread_aware_modules.ThreadAwareConsumerModule,
        thread_aware_modules.Issue503Module])

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
    modules_manager.ModulesManager.DeregisterModule(
        thread_aware_modules.Issue503Module)

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
    # The container shouldn't have been popped, and still be in the store
    self.assertEqual(len(test_state.store[test_report.CONTAINER_TYPE]), 1)

    # Try again, but pop
    reports = test_state.GetContainers(containers.Report, True)
    self.assertEqual(len(reports), 1)
    self.assertIsInstance(reports[0], containers.Report)
    # the container was popped this time
    self.assertEqual(len(test_state.store[test_report.CONTAINER_TYPE]), 0)

  def testGetContainerWithMetadataFilter(self):
    """Tests that containers can be retrieved using metadata filters."""
    test_state = state.DFTimewolfState(config.Config)
    test_cont_1 = thread_aware_modules.TestContainer('foo')
    test_cont_2 = thread_aware_modules.TestContainer('bar')
    test_cont_3 = thread_aware_modules.TestContainer('baz')

    test_cont_1.SetMetadata('metadata_key', '1')
    test_cont_2.SetMetadata('metadata_key', '2')
    test_cont_3.SetMetadata('metadata_key', '3')

    test_state.StoreContainer(test_cont_1)
    test_state.StoreContainer(test_cont_2)
    test_state.StoreContainer(test_cont_3)

    # Test incorrect filters retrieve nothing
    filtered = test_state.GetContainers(thread_aware_modules.TestContainer,
                                        False,
                                        'metadata_key',
                                        'incorrect_value')
    full_list = test_state.GetContainers(thread_aware_modules.TestContainer)
    self.assertEqual(len(filtered), 0)  # None retrieved
    self.assertEqual(len(full_list), 3)  # None removed since none were popped

    filtered = test_state.GetContainers(thread_aware_modules.TestContainer,
                                        False,
                                        'incorrect_key',
                                        'metadata_value')
    full_list = test_state.GetContainers(thread_aware_modules.TestContainer)
    self.assertEqual(len(filtered), 0)  # None retrieved
    self.assertEqual(len(full_list), 3)  # None removed since none were popped

    # Test retrieval, without popping
    filtered = test_state.GetContainers(thread_aware_modules.TestContainer,
                                        False,
                                        'metadata_key',
                                        '1')
    full_list = test_state.GetContainers(thread_aware_modules.TestContainer)
    self.assertEqual(len(filtered), 1)  # One retrieved
    self.assertEqual(len(full_list), 3)  # None removed since none were popped
    self.assertEqual(filtered[0].value, 'foo')
    self.assertEqual(filtered[0].metadata['metadata_key'], '1')

    # Test retrieval, with popping
    filtered = test_state.GetContainers(thread_aware_modules.TestContainer,
                                        True,
                                        'metadata_key',
                                        '1')
    remaining = test_state.GetContainers(thread_aware_modules.TestContainer)
    self.assertEqual(len(filtered), 1)  # One retrieved
    self.assertEqual(len(remaining), 2)  # One popped
    self.assertEqual(filtered[0].value, 'foo')
    self.assertEqual(filtered[0].metadata['metadata_key'], '1')
    self.assertEqual([c.value for c in remaining], ['bar', 'baz'])

  def testGetContainerWithMetadataFilterFailures(self):
    """Tests Runtime Errors retriving containers with a metadata filter."""
    test_state = state.DFTimewolfState(config.Config)

    with self.assertRaises(RuntimeError):
      test_state.GetContainers(containers.Report, False, 'key', '')

    with self.assertRaises(RuntimeError):
      test_state.GetContainers(containers.Report, False, '', 'value')

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
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PreProcess')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PostProcess')
  # pylint: enable=line-too-long
  def testProcessThreadAwareModule(self,
      mock_post_process,
      mock_pre_process,
      mock_threaded_process):
    """Tests the ThreadAwareModules process functions are correctly called."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.threaded_no_preflights, TEST_MODULES)
    test_state.SetupModules()
    test_state.RunModules()
    self.assertEqual(mock_threaded_process.call_count, 3)
    self.assertEqual(mock_post_process.call_count, 1)
    self.assertEqual(mock_pre_process.call_count, 1)
    self.assertEqual(3,
        len(test_state.GetContainers(thread_aware_modules.TestContainer)))

  def testThreadAwareModuleContainerHandling(self):
    """Tests that a ThreadAwareModule handles containers correctly."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.threaded_no_preflights, TEST_MODULES)
    test_state.SetupModules()
    test_state.RunModules()

    self.assertEqual(len(test_state.errors), 0)

    # With no mocks, the first module generates 3 TestContainers, and 1
    # TestContainerTwo. The Test ThreadAwareConsumerModule is threaded on
    # and modifies TestContainer, modifies TestContainerTwo, and generates
    # a TestContainerThree each.
    values = [container.value for container in test_state.GetContainers(
        thread_aware_modules.TestContainer)]
    expected_values = ['one appended', 'two appended', 'three appended']

    self.assertEqual(sorted(values), sorted(expected_values))
    self.assertEqual(
        test_state.GetContainers(
            thread_aware_modules.TestContainerTwo)[0].value,
        'one,two,three appended appended appended'
        )

    values = [container.value for container in test_state.GetContainers(
        thread_aware_modules.TestContainerThree)]
    expected_values = ['output one', 'output two', 'output three']

    self.assertEqual(sorted(values), sorted(expected_values))

  # pylint: disable=line-too-long
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PreProcess')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.Process')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PostProcess')
  # pylint: enable=line-too-long
  def testThreadAwareModulePreProcessFailure(self,
      mock_post_process,
      mock_process,
      mock_pre_process):
    """Tests that if PreProcess exceptions, Process and PostProcess are not
    called."""
    mock_pre_process.side_effect = \
        errors.DFTimewolfError('Exception thrown', critical=False)

    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.threaded_no_preflights, TEST_MODULES)
    test_state.SetupModules()
    test_state.RunModules()

    self.assertEqual(mock_pre_process.call_count, 1)
    self.assertEqual(mock_process.call_count, 0)
    self.assertEqual(mock_post_process.call_count, 0)

  # pylint: disable=line-too-long
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PreProcess')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.Process')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PostProcess')
  # pylint: enable=line-too-long
  def testThreadAwareModuleProcessFailure(self,
      mock_post_process,
      mock_process,
      mock_pre_process):
    """Tests that if Process exceptions, PostProcess is still called."""
    mock_process.side_effect = \
        errors.DFTimewolfError('Exception thrown', critical=False)

    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.threaded_no_preflights, TEST_MODULES)
    test_state.SetupModules()
    test_state.RunModules()

    self.assertEqual(mock_pre_process.call_count, 1)
    self.assertEqual(mock_process.call_count, 3)
    self.assertEqual(mock_post_process.call_count, 1)

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

  def testThreadAwareModuleContainerReuse(self):
    """Tests that containers are handled properly when they are configured to
    pop from the state by a ThreadAwareModule that uses the same container type
    for input and output.

    Ref: https://github.com/log2timeline/dftimewolf/issues/503
    """
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.StoreContainer(thread_aware_modules.TestContainer('one'))
    test_state.StoreContainer(thread_aware_modules.TestContainer('two'))
    test_state.StoreContainer(thread_aware_modules.TestContainer('three'))
    test_state.LoadRecipe(test_recipe.issue_503_recipe, TEST_MODULES)
    test_state.SetupModules()
    test_state.RunModules()

    values = [container.value for container in test_state.GetContainers(
        thread_aware_modules.TestContainer)]
    expected_values = ['one Processed',
                       'two Processed',
                       'three Processed']
    self.assertEqual(sorted(values), sorted(expected_values))

  def testContainerDedupe(self):
    """Tests the DFTimewolfState.DedupeContainers method."""
    test_state = state.DFTimewolfState(config.Config)
    test_state.command_line_options = {}
    test_state.StoreContainer(thread_aware_modules.TestContainer('one'))
    test_state.StoreContainer(thread_aware_modules.TestContainer('one'))
    test_state.StoreContainer(thread_aware_modules.TestContainer('two'))
    test_state.DedupeContainers(thread_aware_modules.TestContainer)
    conts = test_state.GetContainers(thread_aware_modules.TestContainer)

    self.assertEqual(len(conts), 2)
    for value in [c.value for c in conts]:
      self.assertIn(value, ['one', 'two'])


class StateWithCDMTest(unittest.TestCase):
  """Tests for the DFTimewolfStateWithCDM class.

  We're only testing methods that were overridden from the base class."""

  def setUp(self):
    """Registers the dummy modules and recipe to be used in tests."""
    modules_manager.ModulesManager.RegisterModules([
        modules.DummyModule1,
        modules.DummyModule2,
        modules.DummyPreflightModule,
        thread_aware_modules.ContainerGeneratorModule,
        thread_aware_modules.ThreadAwareConsumerModule,
        thread_aware_modules.Issue503Module])

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
    modules_manager.ModulesManager.DeregisterModule(
        thread_aware_modules.Issue503Module)

  def testLoadRecipe(self):
    """Tests Loading a recipe."""
    cdm = CursesDisplayManager()
    test_state = state.DFTimewolfStateWithCDM(config.Config, cdm)

    with mock.patch.object(cdm, 'EnqueuePreflight') as mock_enqueue_preflight, \
        mock.patch.object(cdm, 'EnqueueModule') as mock_enqueue_module, \
        mock.patch.object(cdm, 'Draw') as mock_draw:
      test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)
    # pylint: disable=protected-access
    self.assertIn('DummyModule1', test_state._module_pool)
    self.assertIn('DummyModule2', test_state._module_pool)
    self.assertIn('DummyPreflightModule', test_state._module_pool)
    self.assertEqual(len(test_state._module_pool), 3)

    mock_enqueue_preflight.assert_has_calls([
        mock.call('DummyPreflightModule', [], None)])
    self.assertEqual(mock_enqueue_preflight.call_count, 1)

    mock_enqueue_module.assert_has_calls([
        mock.call('DummyModule1', [], None),
        mock.call('DummyModule2', ['DummyModule1'], None)])
    self.assertEqual(mock_enqueue_module.call_count, 2)

    mock_draw.assert_called_once_with()

  @mock.patch('tests.test_modules.modules.DummyPreflightModule.Process')
  @mock.patch('tests.test_modules.modules.DummyPreflightModule.SetUp')
  def testProcessPreflightModules(self, mock_setup, mock_process):
    """Tests that preflight's process function is called correctly."""
    cdm = CursesDisplayManager()
    test_state = state.DFTimewolfStateWithCDM(config.Config, cdm)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)

    with mock.patch.object(cdm, 'UpdateModuleStatus') as mock_update_status:
      test_state.RunPreflights()

    mock_setup.assert_called_with()
    mock_process.assert_called_with()
    mock_update_status.assert_has_calls([
        mock.call('DummyPreflightModule', Status.SETTINGUP),
        mock.call('DummyPreflightModule', Status.PENDING),
        mock.call('DummyPreflightModule', Status.PROCESSING),
        mock.call('DummyPreflightModule', Status.COMPLETED)])
    self.assertEqual(mock_update_status.call_count, 4)

  @mock.patch('tests.test_modules.modules.DummyPreflightModule.Process')
  @mock.patch('tests.test_modules.modules.DummyPreflightModule.SetUp')
  def testProcessNamedPreflightModules(self, mock_setup, mock_process):
    """Tests that preflight's process function is called correctly."""
    cdm = CursesDisplayManager()
    test_state = state.DFTimewolfStateWithCDM(config.Config, cdm)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.named_modules_contents, TEST_MODULES)

    with mock.patch.object(cdm, 'UpdateModuleStatus') as mock_update_status:
      test_state.RunPreflights()

    mock_setup.assert_called_with()
    mock_process.assert_called_with()

    mock_setup.assert_called_with()
    mock_process.assert_called_with()
    mock_update_status.assert_has_calls([
        mock.call('DummyPreflightModule-runtime', Status.SETTINGUP),
        mock.call('DummyPreflightModule-runtime', Status.PENDING),
        mock.call('DummyPreflightModule-runtime', Status.PROCESSING),
        mock.call('DummyPreflightModule-runtime', Status.COMPLETED)])
    self.assertEqual(mock_update_status.call_count, 4)

  @mock.patch('tests.test_modules.modules.DummyModule2.Process')
  @mock.patch('tests.test_modules.modules.DummyModule1.Process')
  def testProcessModules(self, mock_process1, mock_process2):
    """Tests that modules' process functions are correctly called."""
    cdm = CursesDisplayManager()
    test_state = state.DFTimewolfStateWithCDM(config.Config, cdm)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)

    with mock.patch.object(cdm, 'UpdateModuleStatus') as mock_update_status:
      test_state.SetupModules()
      test_state.RunModules()
    mock_update_status.assert_has_calls([
        mock.call('DummyModule1', Status.SETTINGUP),
        mock.call('DummyModule1', Status.PENDING),
        mock.call('DummyModule2', Status.SETTINGUP),
        mock.call('DummyModule2', Status.PENDING),
        mock.call('DummyModule1', Status.PROCESSING),
        mock.call('DummyModule1', Status.COMPLETED),
        mock.call('DummyModule2', Status.PROCESSING),
        mock.call('DummyModule2', Status.COMPLETED)], True)
    self.assertEqual(mock_update_status.call_count, 8)

    mock_process1.assert_called_with()
    mock_process2.assert_called_with()

  @mock.patch('tests.test_modules.modules.DummyModule2.Process')
  @mock.patch('tests.test_modules.modules.DummyModule1.Process')
  def testProcessNamedModules(self, mock_process1, mock_process2):
    """Tests that modules' process functions are correctly called."""
    cdm = CursesDisplayManager()
    test_state = state.DFTimewolfStateWithCDM(config.Config, cdm)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.named_modules_contents, TEST_MODULES)

    with mock.patch.object(cdm, 'UpdateModuleStatus') as mock_update_status:
      test_state.SetupModules()
      test_state.RunModules()
    mock_update_status.assert_has_calls([
        mock.call('DummyModule1', Status.SETTINGUP),
        mock.call('DummyModule1', Status.PENDING),
        mock.call('DummyModule2', Status.SETTINGUP),
        mock.call('DummyModule2', Status.PENDING),
        mock.call('DummyModule1-2', Status.SETTINGUP),
        mock.call('DummyModule1-2', Status.PENDING),
        mock.call('DummyModule2-2', Status.SETTINGUP),
        mock.call('DummyModule2-2', Status.PENDING),
        mock.call('DummyModule1', Status.PROCESSING),
        mock.call('DummyModule1', Status.COMPLETED),
        mock.call('DummyModule2', Status.PROCESSING),
        mock.call('DummyModule2', Status.COMPLETED),
        mock.call('DummyModule1-2', Status.PROCESSING),
        mock.call('DummyModule1-2', Status.COMPLETED),
        mock.call('DummyModule2-2', Status.PROCESSING),
        mock.call('DummyModule2-2', Status.COMPLETED)], True)
    self.assertEqual(mock_update_status.call_count, 16)

    # pylint: disable=protected-access
    self.assertIn('DummyModule1', test_state._threading_event_per_module)
    self.assertIn('DummyModule2', test_state._threading_event_per_module)
    self.assertIn('DummyModule1-2', test_state._threading_event_per_module)
    self.assertIn('DummyModule2-2', test_state._threading_event_per_module)
    self.assertEqual(mock_process1.call_count, 2)
    self.assertEqual(mock_process2.call_count, 2)

  # pylint: disable=line-too-long
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.Process')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PreProcess')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PostProcess')
  # pylint: enable=line-too-long
  def testProcessThreadAwareModule(self,
      mock_post_process,
      mock_pre_process,
      mock_threaded_process):
    """Tests the ThreadAwareModules process functions are correctly called."""
    cdm = CursesDisplayManager()
    test_state = state.DFTimewolfStateWithCDM(config.Config, cdm)
    test_state.command_line_options = {}
    test_state.LoadRecipe(test_recipe.threaded_no_preflights, TEST_MODULES)

    # pylint: disable=line-too-long
    with mock.patch('threading.current_thread') as mock_current_thread, \
        mock.patch.object(cdm, 'UpdateModuleStatus') as mock_update_status, \
        mock.patch.object(cdm, 'UpdateModuleThreadState') as module_update_thread_state:
      mock_current_thread.return_value.getName.return_value = 'ThreadName'
      test_state.SetupModules()
      test_state.RunModules()
    # pylint: enable=line-too-long

    mock_update_status.assert_has_calls([
        mock.call('ContainerGeneratorModule', Status.PENDING),
        mock.call('ThreadAwareConsumerModule', Status.SETTINGUP),
        mock.call('ThreadAwareConsumerModule', Status.PENDING),
        mock.call('ContainerGeneratorModule', Status.PROCESSING),
        mock.call('ContainerGeneratorModule', Status.COMPLETED),
        mock.call('ThreadAwareConsumerModule', Status.PREPROCESSING),
        mock.call('ThreadAwareConsumerModule', Status.PENDING),
        mock.call('ThreadAwareConsumerModule', Status.PROCESSING),
        mock.call('ThreadAwareConsumerModule', Status.POSTPROCESSING),
        mock.call('ThreadAwareConsumerModule', Status.COMPLETED)], True)
    self.assertEqual(mock_update_status.call_count, 11)

    module_update_thread_state.assert_has_calls([
        mock.call('ThreadAwareConsumerModule', Status.RUNNING,
            'ThreadName', 'one'),
        mock.call('ThreadAwareConsumerModule', Status.COMPLETED,
            'ThreadName', 'one'),
        mock.call('ThreadAwareConsumerModule', Status.RUNNING,
            'ThreadName', 'two'),
        mock.call('ThreadAwareConsumerModule', Status.COMPLETED,
            'ThreadName', 'two'),
        mock.call('ThreadAwareConsumerModule', Status.RUNNING,
            'ThreadName', 'three'),
        mock.call('ThreadAwareConsumerModule', Status.COMPLETED,
            'ThreadName', 'three')], True)
    self.assertEqual(module_update_thread_state.call_count, 6)

    self.assertEqual(mock_threaded_process.call_count, 3)
    self.assertEqual(mock_post_process.call_count, 1)
    self.assertEqual(mock_pre_process.call_count, 1)
    self.assertEqual(3,
        len(test_state.GetContainers(thread_aware_modules.TestContainer)))

  @mock.patch('tests.test_modules.modules.DummyModule2.Process')
  @mock.patch('tests.test_modules.modules.DummyModule1.Process')
  def testProcessErrors(self, mock_process1, mock_process2):
    """Tests that module's errors are correctly caught."""
    cdm = CursesDisplayManager()
    with mock.patch.object(cdm, 'EnqueueMessage') as mock_enqueue_message:
      test_state = state.DFTimewolfStateWithCDM(config.Config, cdm)
      test_state.command_line_options = {}
      test_state.LoadRecipe(test_recipe.contents, TEST_MODULES)
      mock_process1.side_effect = Exception('asd')
      test_state.SetupModules()
      with self.assertRaises(errors.CriticalError):
        test_state.RunModules()
      mock_process1.assert_called_with()

    mock_enqueue_message.assert_has_calls([
        mock.call('dftimewolf',
            'An unknown error occurred in module DummyModule1: asd', True)])
    mock_enqueue_message.assert_called_once()

    # Process() in module 2 is never called since the failure in Module1
    # will abort execution
    mock_process2.assert_not_called()
    self.assertEqual(len(test_state.global_errors), 1)
    error = test_state.global_errors[0]
    self.assertIn('An unknown error occurred in module DummyModule1: asd',
                  error.message)
    self.assertTrue(error.critical)

  # pylint: disable=line-too-long
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PreProcess')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.Process')
  @mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PostProcess')
  # pylint: enable=line-too-long
  def testThreadAwareModuleProcessFailure(self,
      mock_post_process,
      mock_process,
      mock_pre_process):
    """Tests that if Process exceptions, PostProcess is still called."""
    mock_process.side_effect = \
        errors.DFTimewolfError('Exception thrown', critical=False)

    cdm = CursesDisplayManager()
    with mock.patch.object(cdm, 'EnqueueMessage') as mock_enqueue_message:
      test_state = state.DFTimewolfStateWithCDM(config.Config, cdm)
      test_state.command_line_options = {}
      test_state.LoadRecipe(test_recipe.threaded_no_preflights, TEST_MODULES)
      test_state.SetupModules()
      test_state.RunModules()

    mock_enqueue_message.assert_has_calls([
        mock.call('ThreadAwareConsumerModule', 'Exception thrown', True)])
    mock_enqueue_message.assert_called_once()

    self.assertEqual(mock_pre_process.call_count, 1)
    self.assertEqual(mock_process.call_count, 3)
    self.assertEqual(mock_post_process.call_count, 1)


if __name__ == '__main__':
  unittest.main()
