"""Base class for LLM provider interactions."""
from typing import FrozenSet, List, Optional, TYPE_CHECKING
from typing import overload

import pandas as pd

from dftimewolf.lib import logging_utils
from dftimewolf.lib import module
from dftimewolf.lib import state as state_lib
from dftimewolf.lib.containers import containers
from dftimewolf.lib.processors.llmproviders import manager as llm_manager

if TYPE_CHECKING:
  from dftimewolf.lib.processors.llmproviders import interface as llm_interface


class LLMProcessorBase(module.BaseModule):
  """A Base Processor for using (L)LMs to process dataframes.

  Attributes:
    logger: the dftimewolf logger.
    model_name: the name of the model to use.
    provider: the LLM provider instance.
    task: the (L)LM task or pipeline to process.
  """
  def __init__(
      self,
      state: state_lib.DFTimewolfState,
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
    self.logger: logging_utils.WolfLogger = logger
    self.model_name: Optional[str] = None
    self.provider: Optional[llm_interface.LLMProvider] = None
    self.task: Optional[str] = None

  @overload
  def SetUp(self, provider_name: str, model_name: str, task: str):
    ...

  def SetUp(self, provider_name: str, model_name: str, task: str):
    """Sets up the parameters for processing containers with a LLM provider.

    Args:
      provier_name: the LLM provider name
      model_name: the name of the LLM model to use.
      task: the LLM task/pipeline to perform the processing.
    """
    self.provider = llm_manager.LLMProviderManager.GetProvider(
        provider_name=provider_name
    )()

    if model_name not in self.provider.models:
      self.ModuleError(
          f'Model {model_name} is not supported by the LLM provider',
          critical=True
      )
    self.model_name = model_name

    if task not in self.provider.models[model_name]['tasks']:
      self.ModuleError(
          f'Task {task} is not supported by the LLM provider.',
          critical=True
      )
    self.task = task


class DataFrameLLMProcessor(LLMProcessorBase):
  """A class for processing dataframes using a LLM provider.

  Attributes:
    logger (WolfLogger): the dftimewolf logger.
    model_name (str): the name of the model to use.
    task (str): the (L)LM task or pipeline to process.
  """
  def __init__(
      self,
      state: state_lib.DFTimewolfState,
      logger: logging_utils.WolfLogger,
      name: Optional[str] = None,
      critical: bool = False,
  ) -> None:
    """Initializes a LLM base processor.

    Args:
      state: recipe state.
      logger: the dftimewolf logger.
      name: The module's runtime name.
      critical: True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super().__init__(state, logger, name, critical)
    self.columns_to_process: list[str] = []

  def SetUp(self, provider_name: str, task: str, model_name: str, columns_to_process: str) -> None:
    """Sets up the parameters for processing dataframes with a LLM provider.

    Args:
      task: the LLM task/pipeline to perform the processing.
      model_name: the name of the LLM model to use.
      columns_to_process: a comma-separated list of column names that should be
          processed.
    """
    super().SetUp(provider_name=provider_name, model_name=model_name, task=task)
    self.columns_to_process = [x for x in columns_to_process.split(',') if x]
    if len(self.columns_to_process) == 0:
      self.ModuleError('No columns to process', critical=True)

  def _ProcessDataFrame(self, dataframe: pd.DataFrame) -> None:
    """Processes a dataframe using a LLM provider.

    The actual processing task needs to be implemented by the specific subclass
    interfacing with the LLM provider.

    Args:
      dataframe: the Pandas dataframe to process.

    Raises:
      ValueError: if the dataframe does not contain the specified columns.
    """
    if not set(dataframe.columns).issuperset(self.columns_to_process):
      raise ValueError(
          'Dataframe does not contain all the specified columns'
      )

  def Process(self) -> None:
    """Processes DataFrame containers using a LLM provider."""
    dataframe_containers = self.GetContainers(containers.DataFrame)
    for dataframe_container in dataframe_containers:
      try:
        self._ProcessDataFrame(dataframe_container.data_frame)
      except ValueError as error:
        self.ModuleError(
            f'Error processing dataframe {dataframe_container.name}: {error}'
        )
