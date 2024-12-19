"""Tests the base LLM processor module."""
import json
import unittest
import mock

import pandas as pd

from dftimewolf import config
from dftimewolf.lib.containers import containers
from dftimewolf.lib import state as state_lib
from dftimewolf.lib import errors
from dftimewolf.lib.processors import llm_base
from dftimewolf.lib.processors.llmproviders import interface
from dftimewolf.lib.processors.llmproviders import manager as llm_manager
from dftimewolf.lib.logging_utils import WolfLogger


class FakeLLMProvider(interface.LLMProvider):
  """Fake LLMProvider for testing."""
  NAME = 'test'

  def Generate(self, prompt: str, model: str, **kwargs) -> str:
    return 'test'

  def GenerateWithHistory(self, prompt: str, model: str, **kwargs) -> str:
    return 'test'



class DataFrameLLMProcessorTest(unittest.TestCase):
  """Tests for the DataFrameLLMProcessor."""

  def setUp(self):
    """Tests that the processor can be initialized."""
    llm_manager.LLMProviderManager.RegisterProvider(FakeLLMProvider)
    config.Config.LoadExtraData(json.dumps(
        {
            "llm_providers": {
                "test": {
                    "options": {},
                    "models": {
                        "test_model": {
                            "options": {},
                            "tasks": ["test_task"]
                        }
                    }
                }
            }
        }
    ).encode('utf-8'))

    self.logger = WolfLogger('test')
    self.test_state = state_lib.DFTimewolfState(config.Config)
    self.logger = WolfLogger(name='test logger')

  def tearDown(self):
    llm_manager.LLMProviderManager.ClearRegistration()
    config.Config.ClearExtra()

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    llm_base_processor = llm_base.DataFrameLLMProcessor(
        state=self.test_state, logger=self.logger)
    self.assertIsNotNone(llm_base_processor)
    self.assertIsNone(llm_base_processor.model_name)
    self.assertEqual(llm_base_processor.columns_to_process, [])
    self.assertIsNone(llm_base_processor.task)
    self.assertEqual(llm_base_processor.logger, self.logger)

  def testSetUp(self):
    """Tests the SetUp method."""
    llm_base_processor = llm_base.DataFrameLLMProcessor(
        state=self.test_state, logger=self.logger)
    with self.assertRaisesRegex(
        errors.DFTimewolfError,
        r'unknown_model is not supported by the LLM provider'):
      llm_base_processor.SetUp(
          provider_name='test',
          task='unknown_task',
          model_name='unknown_model',
          columns_to_process='a,b,c')

    with self.assertRaisesRegex(
        errors.DFTimewolfError, r'is not supported by the LLM provider'):
      llm_base_processor.SetUp(
          provider_name='test',
          task='unknown_task',
          model_name='test_model',
          columns_to_process='a,b,c'
      )

    with self.assertRaisesRegex(
        errors.DFTimewolfError, r'No columns to process'):
      llm_base_processor.SetUp(
          provider_name='test',
          task='test_task',
          model_name='test_model',
          columns_to_process='')

    llm_base_processor.SetUp(
        provider_name='test',
        task='test_task',
        model_name='test_model',
        columns_to_process='a,b,c')
    self.assertEqual(llm_base_processor.task, 'test_task')
    self.assertEqual(llm_base_processor.model_name, 'test_model')
    self.assertEqual(llm_base_processor.columns_to_process, ['a', 'b', 'c'])

  def testProcess(self):
    """Tests the Process method."""
    container = containers.DataFrame(
        data_frame=pd.DataFrame(), description="None", name="Test")
    self.test_state.StoreContainer(container)
    llm_base_processor = llm_base.DataFrameLLMProcessor(
        state=self.test_state, logger=self.logger)
    llm_base_processor.SetUp(
        provider_name='test',
        model_name='test_model', task='test_task', columns_to_process='a')
    with mock.patch.object(
        llm_base_processor, 'ModuleError'
    ) as mock_error:
      llm_base_processor.Process()
      mock_error.assert_called_once_with(
          'Error processing dataframe Test: ' +
          'Dataframe does not contain all the ' +
          'specified columns'
      )


if __name__ == '__main__':
  unittest.main()
