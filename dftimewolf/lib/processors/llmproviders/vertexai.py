# -*- coding: utf-8 -*-
"""A LLM provider for Google VertexAI."""

import logging
import os
import requests

import backoff
from google.api_core import exceptions
import google.generativeai as genai
import ratelimit

from dftimewolf.lib.processors.llmproviders import interface
from dftimewolf.lib.processors.llmproviders import manager


# Number of calls to allow within a period.
CALL_LIMIT = 20

# Ratelimit period.
ONE_MINUTE = 60

# Maximum time for backoff.
TEN_MINUTE = 10 * ONE_MINUTE


class VertexAILLMProvider(interface.LLMProvider):
  """A provider interface to VertexAI.

  Attributes:
    chat_session: An ongoing conversation with the model.
  """

  NAME = "vertexai"

  def __init__(self):
    super().__init__()
    self.chat_session: genai.ChatSession | None = None
    self._configure()

  def _configure(self):
    """Configures the genai client."""
    if 'api_key' in self.options:
      genai.configure(api_key=self.options['api_key'])
    elif 'project_id' in self.options or 'zone' in self.options:
      genai.configure(
          project_id=self.options['project_id'],
          zone=self.options['zone']
      )
    elif os.environ.get('GOOGLE_API_KEY'):
      genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
    else:
      raise RuntimeError('API key or project_id/zone must be set.')

  def _get_model(self, model: str) -> genai.GenerativeModel:
    """Returns the generative model."""
    model_name = f"models/{model}"
    generation_config = self.models[model]['options'].get('generative_config')
    safety_settings = self.models[model]['options'].get('safety_settings')
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
        safety_settings=safety_settings
    )

  @backoff.on_exception(
      backoff.expo,
      (
          exceptions.ResourceExhausted,
          exceptions.ServiceUnavailable,
          exceptions.GoogleAPIError,
          exceptions.InternalServerError,
          exceptions.Cancelled,
          ratelimit.RateLimitException,
      ),
      max_time=TEN_MINUTE,
      on_backoff=(
          lambda x: log.info(
              f'Backoff attempt #{x["tries"]} after {x["wait"]}s'
          )
      )
  )
  @ratelimit.limits(calls=CALL_LIMIT, period=ONE_MINUTE)
  def Generate(self, prompt: str, model: str, **kwargs) -> str:
    """Generates text from the LLM provider.

    Args:
      prompt: The prompt to use for the generation.
      model: The provider model to use.
      kwargs: Optional arguments to configure the provider.

    Returns:
      The model output.

    Raises:
      StopCandidateException or Exception when an error occurs when
          generating content.
    """
    genai_model = self._get_model(model)
    try:
      response = genai_model.generate_content(contents=prompt, **kwargs)
    except genai.types.generation_types.StopCandidateException as e:
      return f"VertexAI LLM response was stopped because of: {e}"
    except Exception as e:
      log.warning("Exception while calling VertexAI: %s", e)
      raise
    return response.text

  @backoff.on_exception(
      backoff.expo,
      (
          exceptions.ResourceExhausted,
          exceptions.ServiceUnavailable,
          exceptions.GoogleAPIError,
          exceptions.InternalServerError,
          exceptions.Cancelled,
          ratelimit.RateLimitException,
      ),
      max_time=TEN_MINUTE,
      on_backoff=(
          lambda x: log.info(
            f'Backoff attempt #{x["tries"]} after {x["wait"]}s'
          )
      )
  )
  @ratelimit.limits(calls=CALL_LIMIT, period=ONE_MINUTE)
  def GenerateWithHistory(self, prompt: str, model: str, **kwargs) -> str:
    """Generates text from the provider with history."""
    if not self.chat_session:
      self.chat_session = self._get_model().start_chat()
    try:
      response = self.chat_session.send_message(prompt, **kwargs)
    except genai.types.generation_types.StopCandidateException as e:
      return f"VertexAI LLM response was stopped because of: {e}"
    except Exception as e:
      log.warning("Exception while calling VertexAI: %s", e)
      raise

    text_response = ",".join(
        [part.text for part in response.candidates[0].content.parts]
    )
    return text_response


manager.LLMProviderManager.RegisterProvider(VertexAILLMProvider)