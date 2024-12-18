# -*- coding: utf-8 -*-
"""A LLM provider for the Ollama framework."""

import requests
from typing import Any

from dftimewolf.lib.processors.llmproviders import interface
from dftimewolf.lib.processors.llmproviders import manager


DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_OUTPUT_TOKENS = 8192


class OllamaLLMProvider(interface.LLMProvider):
  """A provider interface to the Ollama framework.

  Attributes:
    chat_history: A list of Ollama interactions (user/assistant).
    models: a dictionary of models being served from the Ollama service.
    options: a dictionary of parameters to connect to an Ollama service.
  """

  NAME = "ollama"

  def __init__(self):
    super().__init__()
    self.chat_history: list[dict[str, str]] = []

  def _make_post_request(
      self,
      request_body: dict[str, Any],
      resource: str = '/api/generate/'
  ) -> requests.Response:
    """Makes a POST request to the Ollama REST API service.

    Args:
      request_body: The body of the request in JSON format.
      resource: The Ollama REST API endpoint.

    Returns:
      The response from the server..
    """
    url = self.options['server_url'] + resource
    return requests.post(
        url,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        json=request_body,
        allow_redirects=True
    )

  def _get_request_options(
      self,
      model: str,
      user_args: dict[str, Any] | None = None
  ) -> dict[str, Any]:
    """Gets the API request options from the user/configuration/default values.

    Args:
      user_args: user provided args.

    Returns:
      A dictionary of request options.
    """
    if 'temperature' in user_args:
      temperatue = user_args['temperature']
    else:
      temperature = self.models[model].get(
          'temperature', DEFAULT_TEMPERATURE
      )
    if 'max_output_tokens' in user_args:
      max_output_tokens = user_args['max_output_tokens']
    else:
      max_output_tokens = self.models[model].get(
          'max_output_tokens', DEFAULT_MAX_OUTPUT_TOKENS
      )
    return {
        'temperature': temperature,
        'num_predict': max_output_tokens,
    }

  def Generate(self, prompt: str, model: str, **kwargs) -> str:
    """Generates text from the LLM provider.

    Args:
      prompt: The prompt to use for the generation.
      model: The provider model to use.
      kwargs: Optional arguments to configure the provider.

    Returns:
      The model output.
    """
    request_body = {
        'prompt': prompt,
        'model': model,
        'stream': self.models[model].get('stream', False),
        'options': self._get_request_options(model, kwargs)
    }
    response = self._make_post_request(request_body)
    if response.status_code != 200:
      raise ValueError(
          f'Error {response.status_code} when generating text: '
          f'{response.text}'
      )
    model_response = response.json().get('response', '').strip()
    return model_response

  def GenerateWithHistory(self, prompt: str, model: str, **kwargs) -> str:
    """Generates text from the provider with history.

    Args:
      prompt: The prompt to use for the generation.
      model: The provider model to use.
      kwargs: Optional keyword arguments to configure the provider.

    Returns:
      The model output.
    """
    self.chat_history.append({'role': 'user', 'content': prompt})
    request_body = {
        'messages': self.chat_history,
        'model': model,
        'stream': self.models[model].get('stream', False),
        'options': self._get_request_options(model, kwargs)
    }
    model_response = self._make_post_request(
        request_body,
        resource='/api/chat'
    )
    self.chat_history.append({'role': 'assistant', 'content': model_response})


manager.LLMProviderManager.RegisterProvider(OllamaLLMProvider)