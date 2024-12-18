# -*- coding: utf-8 -*-
"""Base class for LLM provider interactions."""

import abc

from typing import Iterable

from dftimewolf import config
from dftimewolf.lib import logging_utils
from dftimewolf.lib import module
from dftimewolf.lib import state as state_lib
from dftimewolf.lib.containers import containers

BASE_CONFIG_KEY = "llm_providers"


class LLMProvider(abc.ABC):
  """An interface to an LLM provider/service.

  This class provides an interface to a LLM provider/service which a dftimewolf
  processor can use with container data in context for generative AI tasks.

  A LLM service should host one or more models where each model can support
  one or more tasks.  Most models should be able to support the generic "generate"
  task which takes a text prompt as input and returns the model response.

  Other model tasks could be translate, embedding, etc.

  Attributes:
    models: a dictionary of models being served from the Ollama service.
    options: a dictionary of parameters to connect to an Ollama service.
  """

  NAME: str = ""

  def __init__(self):
    """Initialize a LLMProvider."""
    self.models: dict[str, Any] | None = None
    self.options: dict[str, Any] | None = None
    self._LoadConfig()

  def _LoadConfig(self):
    """Loads the LLM provider config from a dftimewolf configuration.

    Configurations are stored as a dictionary under root key "llm_config"
    that maps the provider name to its connection options and supported
    models.

    See config.json for an example.

    Raises:
      RuntimeError - if there are no configurations for the LLM provider.
    """
    llm_provider_config = config.Config.GetExtra(BASE_CONFIG_KEY)
    if not llm_provider_config:
      raise RuntimeError('No LLM configarations found')

    provider_config = llm_provider_config.get(self.NAME)
    if not provider_config:
      raise RuntimeError(f'Configuration for {self.NAME} not found or empty')

    if 'options' not in provider_config:
      raise RuntimeError(f'Connection options not found for {self.NAME}')
    self.options = provider_config['options']

    if 'models' not in provider_config:
      raise RuntimeError(f'No model settings found for {self.NAME}')
    self.models = provider_config['models']

  @abc.abstractmethod
  def Generate(self, prompt: str, model: str, **kwargs) -> str:
    """Generates text from the LLM provider.

    Args:
      prompt: The prompt to use for the generation.
      model: The provider model to use.
      kwargs: Optional keyword arguments to configure the provider.

    Returns:
      The model output.
    """
    raise NotImplementedError

  def GenerateFromTemplate(self, template: str, model: str, **kwargs) -> str:
    """Generates text from the LLM provider using a prompt template.

    Args:
      template: The prompt template.
      model: The provider model to use.
      kwargs: Additional keyword arguments to format the template and
          optional keyword arguments to configure the provider.

    Returns:
      The model output.
    """
    formatter = string.Formatter()
    prompt = formatter.format(template, **kwargs)
    return self.Generate(prompt=prompt, model=model, **kwargs)

  @abc.abstractmethod
  def GenerateWithHistory(self, prompt: str, model: str, **kwargs) -> str:
    """Generates text from the LLM provider using history.

    Args:
      prompt: The prompt to use for the generation.
      model: The provider model to use.
      kwargs: Optional keyword arguments to configure the provider.

    Returns:
      The model output.
    """

  def GenerateFromTemplateWithHistory(
      self,
      template: str,
      model: str,
      **kwargs
  ) -> str:
    """Generates text from the LLM provider using a prompt template with history.

    Args:
      prompt: The prompt to use for the generation.
      model: The provider model to use.
      kwargs: Additional keyword arguments to format the template and
          optional keyword arguments to configure the provider.

    Returns:
      The model output.
    """
    formatter = string.Formatter()
    prompt = formatter.format(template, **kwargs)
    return self.GenerateWithHistory(prompt=prompt, model=model, **kwargs)