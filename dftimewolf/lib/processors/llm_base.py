"""Base class for LLM provider interactions."""
from typing import Optional

import pandas as pd

from dftimewolf.lib import logging_utils
from dftimewolf.lib import module
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers


class LLMProcessorBase(module.BaseModule):
  """A Base Processor for using (L)LMs to process dataframes.

  Attributes:
    columns_to_process (str): the column names of dataframes to process with the
        (L)LM.
    logger (WolfLogger): the dftimewolf logger.
    model_name (str): the name of the model to use.
    task (str): the (L)LM task or pipeline to process.
  """
  SUPPORTED_MODELS = frozenset([])

  SUPPORTED_TASKS = frozenset([])

  def __init__(
      self,
      state: state.DFTimewolfState,
      logger: logging_utils.WolfLogger,
      name: Optional[str] = None,
      critical: bool = False,
  ) -> None:
    """Initializes a LLM base processor.

    Args:
      state (DFTimewolfState): recipe state.
      logger (WolfLogger): the dftimewolf logger.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super().__init__(state=state, name=name, critical=critical)
    self.logger = logger
    self.model_name = None
    self.task = None
    self.columns_to_process = None

  # pylint: disable=arguments-differ
  def SetUp(self, task: str, model_name: str, columns_to_process: str) -> None:
    """Sets up the parameters for processing dataframes with a LLM provider.

    Args:
      task: the LLM task/pipeline to perform the processing.
      model_name: the name of the LLM model to use.
      columns_to_process: a comma-separated list of column names that should be
          processed.
    """
    if task not in self.SUPPORTED_TASKS:
      self.ModuleError(
          f'Task {task} is not supported by the LLM processor.', critical=True)

    self.task = task

    if model_name not in self.SUPPORTED_MODELS:
      self.ModuleError(
          f'Model {model_name} is not supported by the LLM processor',
          critical=True)
    self.model_name = model_name

    self.columns_to_process = [x for x in columns_to_process.split(',') if x]
    if not len(self.columns_to_process):
      self.ModuleError('No columns to process', critical=True)

  def _ProcessDataFrame(self, dataframe: pd.DataFrame) -> None:
    """Processes a dataframe using a LLM provider.

    The actual processing task needs to be implemented by the specific subclass
    interfacing with the LLM provider.

    Args:
      dataframe: the Pandas dataframe to process.

    Raises:
      ValueError if the dataframe does not contain the specified columns.
    """
    if not set(dataframe.columns).issuperset(self.columns_to_process):
      raise ValueError(
          'Dataframe does not contain all the specified columns')

  def Process(self) -> None:
    """Processes DataFrame containers using a LLM provider."""
    dataframe_containers = self.GetContainers(containers.DataFrame)
    for dataframe_container in dataframe_containers:
      try:
        self._ProcessDataFrame(dataframe_container.data_frame)
      except ValueError as error:
        self.ModuleError(
            f'Error processing dataframe {dataframe_container.name}: {error}')
