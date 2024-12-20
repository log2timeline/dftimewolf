# -*- coding: utf-8 -*-
"""A LLM provider for Google Gemini."""

import logging
import os

import backoff
from google.api_core import exceptions
import google.generativeai as genai
import ratelimit

from dftimewolf.lib.processors.llmproviders import interface
from dftimewolf.lib.processors.llmproviders import manager

log = logging.getLogger('dftimewolf.lib.processors.llmproviders.gemini')

# Number of calls to allow within a period.
CALL_LIMIT = 20

# Ratelimit period.
ONE_MINUTE = 60

# Maximum time for backoff.
TEN_MINUTE = 10 * ONE_MINUTE



class GeminiLLMProvider(interface.LLMProvider):
  """A provider interface to Gemini.

  Uses the generativeai library.

  Attributes:
    chat_session: An ongoing conversation with the model.
  """

  NAME = "gemini"

  def __init__(self) -> None:
    """Initializes the VertexAILLMProvider."""
    super().__init__()
    self.chat_session: genai.ChatSession | None = None
    self._configure()

  def _configure(self) -> None:
    """Configures the generativeai client library."""
    api_key = self.options.get('api_key') or os.environ.get('GOOGLE_API_KEY')

    if api_key:
      genai.configure(api_key=api_key)
    else:
      raise RuntimeError('Could not authenticate. '
                         'Please configure an API key to access Gemini.')

  def _get_model(self, model: str) -> genai.GenerativeModel:
    """Returns the Gemini generative model.

    Args:
      model: The generative model name.
    """
    model_name = f"{model}"
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
  @ratelimit.limits(calls=CALL_LIMIT, period=ONE_MINUTE)  # type: ignore
  def Generate(self, prompt: str, model: str, **kwargs: str) -> str:
    """Generates text from the LLM provider.

    Args:
      prompt: The prompt to use for the generation.
      model: The provider model to use.
      kwargs: Optional arguments to configure the provider.

    Returns:
      The model output.

    Raises:
      Exception on an error occuring when generating content.
    """
    genai_model = self._get_model(model)
    try:
      response = genai_model.generate_content(contents=prompt, **kwargs)
    except Exception as e:
      log.warning("Exception while calling VertexAI: %s", e)
      raise
    model_output: str = response.text
    return model_output

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
  @ratelimit.limits(calls=CALL_LIMIT, period=ONE_MINUTE)  # type: ignore
  def GenerateWithHistory(self, prompt: str, model: str, **kwargs: str) -> str:
    """Generates text from the provider with history.

    Args:
      prompt: The prompt to use for the generation.
      model: The provider model to use.
      kwargs: Optional arguments to configure the provider.

    Returns:
      The model output.

    Raises:
      Exception on an error occuring when generating content.
    """
    if not self.chat_session:
      self.chat_session = self._get_model(model).start_chat()
    try:
      response = self.chat_session.send_message(prompt, **kwargs)
    except Exception as e:
      log.warning("Exception while calling VertexAI: %s", e)
      raise

    # text is a quick accessor equivalent to
    # `self.candidates[0].content.parts[0].text`
    text_response: str = response.text
    return text_response

  def AskGemini(self, prompt: str, model: str) -> str:
    """Ask Gemini."""
    return str(self.Generate(prompt, model))


manager.LLMProviderManager.RegisterProvider(GeminiLLMProvider)
