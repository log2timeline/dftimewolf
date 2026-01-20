"""Unit tests for the module runner class."""

# pylint: disable=line-too-long

from unittest import mock
import time

from absl.testing import absltest
from absl.testing import parameterized

from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.modules import module_runner

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


class ModuleRunnerTest(parameterized.TestCase):
  """Unit tests for the module runner class."""

  def setUp(self):
    """Common test setup."""
    super().setUp()

    modules_manager.ModulesManager.RegisterModules([
        modules.DummyModule1,
        modules.DummyModule2,
        modules.DummyPreflightModule,
        thread_aware_modules.ContainerGeneratorModule,
        thread_aware_modules.ThreadAwareConsumerModule,
        thread_aware_modules.Issue503Module])

    self._mock_telemetry = mock.MagicMock()
    self._mock_publish_message_callback = mock.MagicMock()
    self._mock_logger = mock.MagicMock()

    self._runner = module_runner.ModuleRunner(
        logger=self._mock_logger,
        telemetry_=self._mock_telemetry,
        publish_message_callback=self._mock_publish_message_callback)

  def tearDown(self):
    """Deregister the modules used in tests."""
    modules_manager.ModulesManager.DeregisterModule(modules.DummyModule1)
    modules_manager.ModulesManager.DeregisterModule(modules.DummyModule2)
    modules_manager.ModulesManager.DeregisterModule(modules.DummyPreflightModule)
    modules_manager.ModulesManager.DeregisterModule(thread_aware_modules.ContainerGeneratorModule)
    modules_manager.ModulesManager.DeregisterModule(thread_aware_modules.ThreadAwareConsumerModule)
    modules_manager.ModulesManager.DeregisterModule(thread_aware_modules.Issue503Module)

  def test_BasicRecipe(self):
    """Tests method ordering with basic, single threaded modules."""
    with (mock.patch('tests.test_modules.modules.DummyPreflightModule.SetUp') as mock_dp_1_setup,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.Process') as mock_dp_1_process,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.CleanUp') as mock_dp_1_cleanup,
          mock.patch('tests.test_modules.modules.DummyModule1.SetUp') as mock_dm_1_setup,
          mock.patch('tests.test_modules.modules.DummyModule1.Process') as mock_dm_1_process,
          mock.patch('tests.test_modules.modules.DummyModule2.SetUp') as mock_dm_2_setup,
          mock.patch('tests.test_modules.modules.DummyModule2.Process') as mock_dm_2_process):
      mock_parent = mock.Mock()  # Used to determine call order is correct
      mock_parent.attach_mock(mock_dp_1_setup, 'mock_dp_1_setup')
      mock_parent.attach_mock(mock_dp_1_process, 'mock_dp_1_process')
      mock_parent.attach_mock(mock_dp_1_cleanup, 'mock_dp_1_cleanup')
      mock_parent.attach_mock(mock_dm_1_setup, 'mock_dm_1_setup')
      mock_parent.attach_mock(mock_dm_2_setup, 'mock_dm_2_setup')
      mock_parent.attach_mock(mock_dm_1_process, 'mock_dm_1_process')
      mock_parent.attach_mock(mock_dm_2_process, 'mock_dm_2_process')

      def mock_delay():  # pylint: disable=invalid-name
        # This is used to ensure that even if the first module takes time, the
        # second module waits for it to finish, when combined with checking the
        # call order later.
        time.sleep(1)
      mock_dm_1_process.side_effect = mock_delay

      running_args = {'recipe': test_recipe.basic_recipe}
      running_args['recipe']['preflights'][0]['args'] = {'args': 'none'}
      running_args['recipe']['modules'][0]['args'] = {'runtime_value': 'value 1'}
      running_args['recipe']['modules'][1]['args'] = {'runtime_value': 'value 2'}

      self._runner.Initialise(test_recipe.basic_recipe, TEST_MODULES)
      self._runner.Run(running_args=running_args)

      self.assertEqual(mock_dp_1_setup.call_count, 1)
      self.assertEqual(mock_dp_1_process.call_count, 1)
      self.assertEqual(mock_dm_1_setup.call_count, 1)
      self.assertEqual(mock_dm_2_setup.call_count, 1)
      self.assertEqual(mock_dm_1_process.call_count, 1)
      self.assertEqual(mock_dm_2_process.call_count, 1)
      self.assertEqual(mock_dp_1_cleanup.call_count, 1)

      # Check call ordering
      mock_parent.assert_has_calls([mock.call.mock_dp_1_setup(args='none'),
                                    mock.call.mock_dp_1_process(),
                                    mock.call.mock_dm_1_setup(runtime_value='value 1'),
                                    mock.call.mock_dm_2_setup(runtime_value='value 2'),
                                    mock.call.mock_dm_1_process(),
                                    mock.call.mock_dm_2_process(),
                                    mock.call.mock_dp_1_cleanup()],
                                   any_order=False)

  def test_BasicRecipeWithRuntimeNames(self):
    """Tests method ordering with basic modules, with runtime names."""
    with (mock.patch('tests.test_modules.modules.DummyPreflightModule.SetUp') as mock_dp_1_setup,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.Process') as mock_dp_1_process,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.CleanUp') as mock_dp_1_cleanup,
          mock.patch('tests.test_modules.modules.DummyModule1.SetUp') as mock_dm_1_setup,
          mock.patch('tests.test_modules.modules.DummyModule1.Process') as mock_dm_1_process,
          mock.patch('tests.test_modules.modules.DummyModule2.SetUp') as mock_dm_2_setup,
          mock.patch('tests.test_modules.modules.DummyModule2.Process') as mock_dm_2_process):
      mock_parent = mock.Mock()  # Used to determine call order is correct
      mock_parent.attach_mock(mock_dp_1_setup, 'mock_dp_1_setup')
      mock_parent.attach_mock(mock_dp_1_process, 'mock_dp_1_process')
      mock_parent.attach_mock(mock_dp_1_cleanup, 'mock_dp_1_cleanup')
      mock_parent.attach_mock(mock_dm_1_setup, 'mock_dm_1_setup')
      mock_parent.attach_mock(mock_dm_2_setup, 'mock_dm_2_setup')
      mock_parent.attach_mock(mock_dm_1_process, 'mock_dm_1_process')
      mock_parent.attach_mock(mock_dm_2_process, 'mock_dm_2_process')

      running_args = {'recipe': test_recipe.with_runtime_names}
      running_args['recipe']['preflights'][0]['args'] = {'args': 'none'}

      self._runner.Initialise(test_recipe.with_runtime_names, TEST_MODULES)
      self._runner.Run(running_args=running_args)

      self.assertEqual(mock_dp_1_setup.call_count, 1)
      self.assertEqual(mock_dp_1_process.call_count, 1)
      self.assertEqual(mock_dm_1_setup.call_count, 2)
      self.assertEqual(mock_dm_2_setup.call_count, 2)
      self.assertEqual(mock_dm_1_process.call_count, 2)
      self.assertEqual(mock_dm_2_process.call_count, 2)
      self.assertEqual(mock_dp_1_cleanup.call_count, 1)

      # Check call ordering
      mock_parent.assert_has_calls([mock.call.mock_dp_1_setup(args='none'),
                                    mock.call.mock_dp_1_process(),
                                    mock.call.mock_dm_1_setup(runtime_value='1-1'),
                                    mock.call.mock_dm_2_setup(runtime_value='2-1'),
                                    mock.call.mock_dm_1_setup(runtime_value='1-2'),
                                    mock.call.mock_dm_2_setup(runtime_value='2-2'),
                                    mock.call.mock_dm_1_process(),
                                    mock.call.mock_dm_2_process(),
                                    mock.call.mock_dm_1_process(),
                                    mock.call.mock_dm_2_process(),
                                    mock.call.mock_dp_1_cleanup()],
                                   any_order=False)

  def test_RecipeWithThreadedModules(self):
    """Tests method ordering with threaded modules."""
    with (mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.SetUp') as mock_tacm_setup,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PreProcess') as mock_tacm_preprocess,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.Process') as mock_tacm_process,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PostProcess') as mock_tacm_postprocess):
      mock_parent = mock.Mock()  # Used to determine call order is correct
      mock_parent.attach_mock(mock_tacm_setup, 'mock_tacm_setup')
      mock_parent.attach_mock(mock_tacm_preprocess, 'mock_tacm_preprocess')
      mock_parent.attach_mock(mock_tacm_process, 'mock_tacm_process')
      mock_parent.attach_mock(mock_tacm_postprocess, 'mock_tacm_postprocess')

      # The generator module will create 3 containers with values 'one', 'two', 'three'
      running_args = {'recipe': test_recipe.threaded_no_preflights}
      running_args['recipe']['modules'][0]['args'] = {'runtime_value': 'one,two,three'}

      self._runner.Initialise(test_recipe.threaded_no_preflights, TEST_MODULES)
      self._runner.Run(running_args=running_args)

      mock_parent.assert_has_calls([mock.call.mock_tacm_setup(),
                                    mock.call.mock_tacm_preprocess(),
                                    mock.call.mock_tacm_process(mock.ANY),
                                    mock.call.mock_tacm_process(mock.ANY),
                                    mock.call.mock_tacm_process(mock.ANY),
                                    mock.call.mock_tacm_postprocess()],
                                   any_order=False)

  def test_ContainerHandlingWithThreadedModules(self):
    """Tests container handling and delivery with threaded modules."""
    # The generator module will create 3 containers with values 'one', 'two', 'three'
    running_args = {'recipe': test_recipe.threaded_no_preflights}
    running_args['recipe']['modules'][0]['args'] = {'runtime_value': 'one,two,three'}

    self._runner.Initialise(test_recipe.threaded_no_preflights, TEST_MODULES)

    # Mock out the container cleanup for this test
    self._runner._container_manager.CompleteModule = mock.MagicMock()  # pylint: disable=protected-access

    self._runner.Run(running_args=running_args)

    output_containers = self._runner._container_manager.GetContainers(  # pylint: disable=protected-access
        'ThreadAwareConsumerModule', thread_aware_modules.TestContainerThree)
    self.assertListEqual(sorted([c.value for c in output_containers]),
                         sorted(['output one', 'output two', 'output three']))

    output_containers = self._runner._container_manager.GetContainers(  # pylint: disable=protected-access
        'ThreadAwareConsumerModule', thread_aware_modules.TestContainer)
    self.assertListEqual(sorted([c.value for c in output_containers]),
                         sorted(['one appended', 'two appended', 'three appended']))

  def testThreadAwareModuleContainerReuse(self):
    """Tests that containers are handled properly when they are configured to
    pop from the state by a ThreadAwareModule that uses the same container type
    for input and output.

    Ref: https://github.com/log2timeline/dftimewolf/issues/503
    """
    running_args = {'recipe': test_recipe.issue_503_recipe}

    self._runner.Initialise(test_recipe.issue_503_recipe, TEST_MODULES)

    container_manager = self._runner._container_manager  # pylint: disable=protected-access
    # Mock out the container cleanup for this test
    container_manager.CompleteModule = mock.MagicMock()

    container_manager.StoreContainer(container=thread_aware_modules.TestContainer('one'), source_module='Issue503Module')
    container_manager.StoreContainer(container=thread_aware_modules.TestContainer('two'), source_module='Issue503Module')
    container_manager.StoreContainer(container=thread_aware_modules.TestContainer('three'), source_module='Issue503Module')

    self._runner.Run(running_args=running_args)

    values = [container.value for container in container_manager.GetContainers(
        container_class=thread_aware_modules.TestContainer,
        requesting_module='Issue503Module')]
    expected_values = ['one Processed',
                       'two Processed',
                       'three Processed']
    self.assertEqual(sorted(values), sorted(expected_values))

  def test_PreflightSetUpUnhandledError(self):
    """Tests an error in Preflights SetUp cancels execution of later modules."""
    # If a preflight SetUp fails, then the Process for the same preflight should
    # not be attempted, and no modules SetUp or Process should be attempted.
    with (mock.patch('tests.test_modules.modules.DummyPreflightModule.SetUp') as mock_dp_1_setup,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.Process') as mock_dp_1_process,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.CleanUp') as mock_dp_1_cleanup,
          mock.patch('tests.test_modules.modules.DummyModule1.SetUp') as mock_dm_1_setup,
          mock.patch('tests.test_modules.modules.DummyModule1.Process') as mock_dm_1_process,
          mock.patch('tests.test_modules.modules.DummyModule2.SetUp') as mock_dm_2_setup,
          mock.patch('tests.test_modules.modules.DummyModule2.Process') as mock_dm_2_process):
      mock_dp_1_setup.side_effect = RuntimeError('Test error')

      running_args = {'recipe': test_recipe.basic_recipe}

      self._runner.Initialise(test_recipe.basic_recipe, TEST_MODULES)
      self._runner.Run(running_args=running_args)

      mock_dp_1_setup.assert_called_once()
      mock_dp_1_process.assert_not_called()
      mock_dm_1_setup.assert_not_called()
      mock_dm_2_setup.assert_not_called()
      mock_dm_1_process.assert_not_called()
      mock_dm_2_process.assert_not_called()
      mock_dp_1_cleanup.assert_called_once()

  def test_PreflightProcessUnhandledError(self):
    """Tests an error in Preflights Process cancels execution of later modules."""
    # If a preflight Process fails, then no module shoudl have SetUp or Process
    # called.
    with (mock.patch('tests.test_modules.modules.DummyPreflightModule.SetUp') as mock_dp_1_setup,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.Process') as mock_dp_1_process,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.CleanUp') as mock_dp_1_cleanup,
          mock.patch('tests.test_modules.modules.DummyModule1.SetUp') as mock_dm_1_setup,
          mock.patch('tests.test_modules.modules.DummyModule1.Process') as mock_dm_1_process,
          mock.patch('tests.test_modules.modules.DummyModule2.SetUp') as mock_dm_2_setup,
          mock.patch('tests.test_modules.modules.DummyModule2.Process') as mock_dm_2_process):
      mock_dp_1_process.side_effect = RuntimeError('Test error')

      running_args = {'recipe': test_recipe.basic_recipe}

      self._runner.Initialise(test_recipe.basic_recipe, TEST_MODULES)
      self._runner.Run(running_args=running_args)

      mock_dp_1_setup.assert_called_once()
      mock_dp_1_process.assert_called_once()
      mock_dm_1_setup.assert_not_called()
      mock_dm_2_setup.assert_not_called()
      mock_dm_1_process.assert_not_called()
      mock_dm_2_process.assert_not_called()
      mock_dp_1_cleanup.assert_called_once()

  def test_ModuleSetUpUnhandledError(self):
    """Tests an error in a modules SetUp cancels execution of later modules."""
    # If a module fails in SetUp, then no modules should have Process called.
    with (mock.patch('tests.test_modules.modules.DummyPreflightModule.SetUp') as mock_dp_1_setup,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.Process') as mock_dp_1_process,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.CleanUp') as mock_dp_1_cleanup,
          mock.patch('tests.test_modules.modules.DummyModule1.SetUp') as mock_dm_1_setup,
          mock.patch('tests.test_modules.modules.DummyModule1.Process') as mock_dm_1_process,
          mock.patch('tests.test_modules.modules.DummyModule2.SetUp') as mock_dm_2_setup,
          mock.patch('tests.test_modules.modules.DummyModule2.Process') as mock_dm_2_process):
      mock_dm_1_setup.side_effect = RuntimeError('Test error')

      running_args = {'recipe': test_recipe.basic_recipe}

      self._runner.Initialise(test_recipe.basic_recipe, TEST_MODULES)
      self._runner.Run(running_args=running_args)

      mock_dp_1_setup.assert_called_once()
      mock_dp_1_process.assert_called_once()
      mock_dm_1_setup.assert_called_once()
      mock_dm_2_setup.assert_not_called()
      mock_dm_1_process.assert_not_called()
      mock_dm_2_process.assert_not_called()
      mock_dp_1_cleanup.assert_called_once()

  def test_ModuleProcessUnhandledError(self):
    """Tests an error in a modules Processs cancels execution of later modules."""
    # If a module fails in Process, then dependant modules should not have
    # Process called.
    with (mock.patch('tests.test_modules.modules.DummyPreflightModule.SetUp') as mock_dp_1_setup,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.Process') as mock_dp_1_process,
          mock.patch('tests.test_modules.modules.DummyPreflightModule.CleanUp') as mock_dp_1_cleanup,
          mock.patch('tests.test_modules.modules.DummyModule1.SetUp') as mock_dm_1_setup,
          mock.patch('tests.test_modules.modules.DummyModule1.Process') as mock_dm_1_process,
          mock.patch('tests.test_modules.modules.DummyModule2.SetUp') as mock_dm_2_setup,
          mock.patch('tests.test_modules.modules.DummyModule2.Process') as mock_dm_2_process):
      mock_dm_1_process.side_effect = RuntimeError('Test error')

      running_args = {'recipe': test_recipe.basic_recipe}

      self._runner.Initialise(test_recipe.basic_recipe, TEST_MODULES)
      self._runner.Run(running_args=running_args)

      mock_dp_1_setup.assert_called_once()
      mock_dp_1_process.assert_called_once()
      mock_dm_1_setup.assert_called_once()
      mock_dm_2_setup.assert_called_once()
      mock_dm_1_process.assert_called_once()
      mock_dm_2_process.assert_not_called()
      mock_dp_1_cleanup.assert_called_once()

  def test_ThreadedModuleSetUpUnhandledError(self):
    """Tests an error in SetUp of a threaded module."""
    # If a module fails in SetUp, process methods shouldn't be called.
    with (mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.SetUp') as mock_tacm_setup,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PreProcess') as mock_tacm_preprocess,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.Process') as mock_tacm_process,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PostProcess') as mock_tacm_postprocess):
      mock_tacm_setup.side_effect = RuntimeError('Test error')

      # The generator module will create 3 containers with values 'one', 'two', 'three'
      running_args = {'recipe': test_recipe.threaded_no_preflights}
      running_args['recipe']['modules'][0]['args'] = {'runtime_value': 'one,two,three'}

      self._runner.Initialise(test_recipe.threaded_no_preflights, TEST_MODULES)
      self._runner.Run(running_args=running_args)

      mock_tacm_setup.assert_called_once()
      mock_tacm_preprocess.assert_not_called()
      mock_tacm_process.assert_not_called()
      mock_tacm_postprocess.assert_not_called()

  def test_ThreadedModulePreProcessUnhandledError(self):
    """Tests an error in PreProcess of a threaded module."""
    # If a module fails in PreProcess, other process methods shouldn't be called.
    with (mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.SetUp') as mock_tacm_setup,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PreProcess') as mock_tacm_preprocess,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.Process') as mock_tacm_process,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PostProcess') as mock_tacm_postprocess):
      mock_tacm_preprocess.side_effect = RuntimeError('Test error')

      # The generator module will create 3 containers with values 'one', 'two', 'three'
      running_args = {'recipe': test_recipe.threaded_no_preflights}
      running_args['recipe']['modules'][0]['args'] = {'runtime_value': 'one,two,three'}

      self._runner.Initialise(test_recipe.threaded_no_preflights, TEST_MODULES)
      self._runner.Run(running_args=running_args)

      mock_tacm_setup.assert_called_once()
      mock_tacm_preprocess.assert_called_once()
      mock_tacm_process.assert_not_called()
      mock_tacm_postprocess.assert_not_called()

  def test_ThreadedModuleProcessUnhandledError(self):
    """Tests an error in Process of a threaded module."""
    # If a module fails in Process, Postprecoess is still called.
    with (mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.SetUp') as mock_tacm_setup,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PreProcess') as mock_tacm_preprocess,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.Process') as mock_tacm_process,
          mock.patch('tests.test_modules.thread_aware_modules.ThreadAwareConsumerModule.PostProcess') as mock_tacm_postprocess):
      mock_tacm_process.side_effect = [None, RuntimeError('Test error'), None]

      # The generator module will create 3 containers with values 'one', 'two', 'three'
      running_args = {'recipe': test_recipe.threaded_no_preflights}
      running_args['recipe']['modules'][0]['args'] = {'runtime_value': 'one,two,three'}

      self._runner.Initialise(test_recipe.threaded_no_preflights, TEST_MODULES)
      self._runner.Run(running_args=running_args)

      mock_tacm_setup.assert_called_once()
      mock_tacm_preprocess.assert_called_once()
      self.assertEqual(mock_tacm_process.call_count, 3)
      mock_tacm_postprocess.assert_called_once()

  # TODO - Handled errors (eg, self.ModuleError)


if __name__ == '__main__':
  absltest.main()
