"""Tests the base LLM processor module."""

# pytype: disable=attribute-error


import json
import unittest

import mock
import pandas as pd

from dftimewolf import config
from dftimewolf.lib import errors
from dftimewolf.lib import state as state_lib
from dftimewolf.lib.containers import containers
from dftimewolf.lib.logging_utils import WolfLogger
from dftimewolf.lib.processors import llm_base
from dftimewolf.lib.processors.llmproviders import interface
from dftimewolf.lib.processors.llmproviders import manager as llm_manager
from tests.lib import modules_test_base


class FakeLLMProvider(interface.LLMProvider):
  """Fake LLMProvider for testing."""
  NAME = 'test'

  def Generate(self, prompt: str, model: str, **kwargs) -> str:
    return 'test'

  def GenerateWithHistory(self, prompt: str, model: str, **kwargs) -> str:
    return 'test'


class DataFrameLLMProcessorTest(modules_test_base.ModuleTestBase):
  """Tests for the DataFrameLLMProcessor."""

  def _InitModule(self, test_module: type[llm_base.DataFrameLLMProcessor]
                  ):  # pytype: disable=signature-mismatch
    self._logger = WolfLogger(name='test logger')
    self._test_state = state_lib.DFTimewolfState(config.Config)
    self._module = test_module(self._test_state, logger=self._logger)
    self._test_state._container_manager.ParseRecipe(  # pylint: disable=protected-access
        {'modules': [{'name': self._module.name}]})

  def setUp(self):
    """Tests that the processor can be initialized."""
    llm_manager.LLMProviderManager.RegisterProvider(FakeLLMProvider)
    config.Config.LoadExtraData(json.dumps(
        {
            'llm_providers': {
                'test': {
                    'options': {},
                    'models': {
                        'test_model': {
                            'options': {},
                            'tasks': ['test_task']
                        }
                    }
                }
            }
        }
    ).encode('utf-8'))

    self._InitModule(llm_base.DataFrameLLMProcessor)

  def tearDown(self):
    llm_manager.LLMProviderManager.ClearRegistration()
    config.Config.ClearExtra()

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    self.assertIsNotNone(self._module)
    self.assertIsNone(self._module.model_name)
    self.assertEqual(self._module.columns_to_process, [])
    self.assertIsNone(self._module.task)
    self.assertEqual(self._module.logger, self._logger)

  def testSetUp(self):
    """Tests the SetUp method."""
    with self.assertRaisesRegex(
        errors.DFTimewolfError,
        r'unknown_model is not supported by the LLM provider'):
      self._module.SetUp(
          provider_name='test',
          task='unknown_task',
          model_name='unknown_model',
          columns_to_process='a,b,c')

    with self.assertRaisesRegex(
        errors.DFTimewolfError, r'is not supported by the LLM provider'):
      self._module.SetUp(
          provider_name='test',
          task='unknown_task',
          model_name='test_model',
          columns_to_process='a,b,c'
      )

    with self.assertRaisesRegex(
        errors.DFTimewolfError, r'No columns to process'):
      self._module.SetUp(
          provider_name='test',
          task='test_task',
          model_name='test_model',
          columns_to_process='')

    self._module.SetUp(
        provider_name='test',
        task='test_task',
        model_name='test_model',
        columns_to_process='a,b,c')
    self.assertEqual(self._module.task, 'test_task')
    self.assertEqual(self._module.model_name, 'test_model')
    self.assertEqual(self._module.columns_to_process, ['a', 'b', 'c'])

  def testProcess(self):
    """Tests the Process method."""
    container = containers.DataFrame(
        data_frame=pd.DataFrame(), description="None", name="Test")
    self._module.StoreContainer(container)
    self._module.SetUp(
        provider_name='test',
        model_name='test_model', task='test_task', columns_to_process='a')
    with mock.patch.object(
        self._module, 'ModuleError'
    ) as mock_error:
      self._ProcessModule()
      mock_error.assert_called_once_with(
          'Error processing dataframe Test: ' +
          'Dataframe does not contain all the ' +
          'specified columns - a'
      )


if __name__ == '__main__':
  unittest.main()
