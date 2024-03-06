"""Tests the base LLM processor module."""
import unittest
import mock

import pandas as pd

from dftimewolf import config
from dftimewolf.lib.containers import containers
from dftimewolf.lib import module
from dftimewolf.lib import state
from dftimewolf.lib import errors
from dftimewolf.lib.processors import llm_base
from dftimewolf.lib.logging_utils import WolfLogger

class LLMProcessorBaseTest(unittest.TestCase):
  """Tests for the LLM Processor."""

  def setUp(self):
    """Tests that the processor can be initialized."""
    #self.logger = WolfLogger('test')
    self.test_state = state.DFTimewolfState(config.Config)
    self.logger = WolfLogger(name='test logger')

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    llm_base_processor = llm_base.LLMProcessorBase(
        state=self.test_state, logger=self.logger)
    self.assertIsNotNone(llm_base_processor)
    self.assertIsNone(llm_base_processor.model_name)
    self.assertIsNone(llm_base_processor.columns_to_process)
    self.assertIsNone(llm_base_processor.task)
    self.assertEqual(llm_base_processor.logger, self.logger)

  def testSetUp(self):
    """Tests the SetUp method."""
    llm_base_processor = llm_base.LLMProcessorBase(
        state=self.test_state, logger=self.logger)
    with self.assertRaisesRegex(
        errors.DFTimewolfError,
        r'is not supported by the LLM processor') as error:
      llm_base_processor.SetUp(
          'unknown', model_name='unknown', columns_to_process='a,b,c')

    llm_base_processor.SUPPORTED_TASKS = frozenset(['patched_task'])
    with self.assertRaisesRegex(
        errors.DFTimewolfError, r'is not supported by the LLM processor'):
      llm_base_processor.SetUp(
          task='patched_task', model_name='unknown', columns_to_process='a,b,c')

    llm_base_processor.SUPPORTED_MODELS = frozenset(['patched_model'])
    with self.assertRaisesRegex(
        errors.DFTimewolfError, r'No columns to process'):
      llm_base_processor.SetUp(
          task='patched_task',
          model_name='patched_model',
          columns_to_process='')

    llm_base_processor.SetUp(
          task='patched_task',
          model_name='patched_model',
          columns_to_process='a,b,c')
    self.assertEqual(llm_base_processor.task, 'patched_task')
    self.assertEqual(llm_base_processor.model_name, 'patched_model')
    self.assertEqual(llm_base_processor.columns_to_process, ['a', 'b', 'c'])

  def testProcess(self):
    """Tests the Process method."""
    container = containers.DataFrame(
        data_frame=pd.DataFrame(), description="None", name="Test")
    self.test_state.StoreContainer(container)
    llm_base_processor = llm_base.LLMProcessorBase(
        state=self.test_state, logger=self.logger)
    llm_base_processor.SUPPORTED_MODELS = ['test_model']
    llm_base_processor.SUPPORTED_TASKS = ['test_task']
    llm_base_processor.SetUp(
        model_name='test_model', task='test_task', columns_to_process='a')
    with mock.patch.object(llm_base_processor, 'ModuleError') as mock_error:
      llm_base_processor.Process()
      mock_error.assert_called_once_with(
        'Error processing dataframe Test: Dataframe does not contain all the ' +
        'specified columns'
      )

if __name__ == '__main__':
  unittest.main()
