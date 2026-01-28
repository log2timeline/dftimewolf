"""Base class for LLM provider interactions."""

from typing import TYPE_CHECKING, Any, Callable

import pandas as pd

from dftimewolf.lib import module
from dftimewolf.lib import cache
from dftimewolf.lib import telemetry
from dftimewolf.lib.containers import manager as container_manager
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

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initializes a LLM base processor.

    Args:
      name: The modules runtime name.
      container_manager_: A common container manager object.
      cache_: A common DFTWCache object.
      telemetry_: A common telemetry collector object.
      publish_message_callback: A callback to send modules messages to.
    """
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)
    self.model_name: str
    self.provider: llm_interface.LLMProvider
    self.task: str | None = None

  def SetUp(self, provider_name: str, model_name: str, task: str) -> None:  # pylint: disable=arguments-differ
    """Sets up the parameters for processing containers with a LLM provider.

    Args:
      provider_name: the LLM provider name
      model_name: the name of the LLM model to use.
      task: the LLM task/pipeline to perform the processing.
    """
    provider_class = llm_manager.LLMProviderManager.GetProvider(
      provider_name=provider_name
    )
    self.provider = provider_class()  # pytype: disable=not-instantiable
    assert self.provider  # to appease mypy

    if model_name not in self.provider.models:
      self.ModuleError(
        f"Model {model_name} is not supported by the LLM provider",
        critical=True,
      )
    self.model_name = model_name

    if task not in self.provider.models[model_name]["tasks"]:
      self.ModuleError(
        f"Task {task} is not supported by the LLM provider.", critical=True
      )
    self.task = task

  def _PromptLLM(
    self,
    prompt: str,
    content: bytes | None = None,
    mime_type: str | None = None,
    response_schema: Any = None,
  ) -> str:
    """Prompts the LLM with the given prompt and optional content.

    Args:
      prompt: The prompt to send to the LLM.
      content: The optional file content to send to the LLM.  If content is
        provided, the mime_type must also be provided.
      mime_type: The optional mime type of the content.
      response_schema: The optional response schema to use for the LLM.

    Returns:
      The LLM response.
    """
    # pytype: disable=attribute-error
    # (since provider and model attributes are already checked in setup)
    if content and mime_type:
      return self.provider.Generate(
        prompt=prompt,
        model=self.model_name,
        mime_type=mime_type,
        content=content,
      )  # pytype: disable=wrong-arg-types
    return self.provider.Generate(
      prompt=prompt, model=self.model_name, response_schema=response_schema
    )
    # pytype: enable=attribute-error

  def Process(self) -> None:
    """To be implemented by subclasses."""
    raise NotImplementedError


class DataFrameLLMProcessor(LLMProcessorBase):
  """A class for processing dataframes using a LLM provider.

  Attributes:
    logger: the dftimewolf logger.
    model_name: the name of the model to use.
    task: the (L)LM task or pipeline to process.
  """

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initializes a LLM base processor.

    Args:
      name: The modules runtime name.
      container_manager_: A common container manager object.
      cache_: A common DFTWCache object.
      telemetry_: A common telemetry collector object.
      publish_message_callback: A callback to send modules messages to.
    """
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)

    self.columns_to_process: list[str] = []

  def SetUp(  # pylint: disable=arguments-differ
    self,
    provider_name: str,
    model_name: str,
    task: str,
    columns_to_process: str = "",
  ) -> None:
    """Sets up the parameters for processing dataframes with a LLM provider.

    Args:
      provider_name: the LLM provider name
      model_name: the name of the LLM model to use.
      task: the LLM task/pipeline to perform the processing.
      columns_to_process: a comma-separated list of column names that should be
          processed.
    """
    super().SetUp(provider_name=provider_name, model_name=model_name, task=task)
    self.columns_to_process = [x for x in columns_to_process.split(",") if x]
    if len(self.columns_to_process) == 0:
      self.ModuleError("No columns to process", critical=True)

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
        'Dataframe does not contain all the specified columns - '
        f'{",".join(self.columns_to_process)}'
      )

  def Process(self) -> None:
    """Processes DataFrame containers using a LLM provider."""
    dataframe_containers = self.GetContainers(containers.DataFrame)
    for dataframe_container in dataframe_containers:
      try:
        self._ProcessDataFrame(dataframe_container.data_frame)
      except ValueError as error:
        self.ModuleError(
          f"Error processing dataframe {dataframe_container.name}: {error}"
        )
