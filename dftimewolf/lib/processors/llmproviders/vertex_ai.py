# -*- coding: utf-8 -*-
"""A LLM provider for Google VertexAI."""

import json
import logging
import os

import backoff
from google.api_core import exceptions
from google.oauth2 import service_account
import ratelimit
import vertexai
from vertexai import generative_models

from dftimewolf.lib.processors.llmproviders import interface
from dftimewolf.lib.processors.llmproviders import manager

log = logging.getLogger('dftimewolf.lib.processors.llmproviders.vertex_ai')

# Number of calls to allow within a period.
CALL_LIMIT = 20

# Ratelimit period.
ONE_MINUTE = 60

# Maximum time for backoff.
TEN_MINUTE = 10 * ONE_MINUTE

DEFAULT_ADC_PATH = '.config/gcloud/application_default_credentials.json'


class VertexAILLMProvider(interface.LLMProvider):
  """A provider interface to VertexAI.

  Uses the python vertexai library.

  Attributes:
    chat_session: An ongoing conversation with the model.
  """

  NAME = "vertexai"

  def __init__(self) -> None:
    """Initializes the VertexAILLMProvider."""
    super().__init__()
    self.chat_session: generative_models.ChatSession | None = None
    self._configure()

  def _configure(self) -> None:
    """Configures the vertexai client library.

    Uses the following to authenticate:
    * user specified service account key
    * default service account / application default credentials.
    """
    api_key = self.options.get('api_key') or os.environ.get('GOOGLE_API_KEY')
    project_id = self.options.get('project_id')
    location = self.options.get('region')
    service_account_path = self.options.get('sa_path')

    if service_account_path:
      with open(service_account_path) as sa_file:
        info = json.loads(sa_file.read())
      sa_credential = (
          service_account.Credentials.from_service_account_info(info))
      vertexai.init(
          credentials=sa_credential,
          api_key=api_key,
          project=project_id,
          location=location
      )
    elif (os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or
        (
            os.environ.get('HOME') and
            os.path.exists(os.path.join(os.environ['HOME'],
                                        DEFAULT_ADC_PATH))
        )
    ):
      vertexai.init(api_key=api_key, project=project_id, location=location)
    else:
      raise RuntimeError('Could not authenticate. '
                         'Please configure a credential to access VertexAI.')

  def _get_model(self, model: str) -> generative_models.GenerativeModel:
    """Returns the VertexAI generative model.

    Args:
      model: The generative model name.
    """
    model_name = f"models/{model}"
    generation_config = self.models[model]['options'].get('generative_config')
    safety_settings = [
        generative_models.SafetySetting(
            category=generative_models.HarmCategory[
                safety_setting['category']
            ],
            threshold=generative_models.HarmBlockThreshold[
                safety_setting['threshold']
            ]
        ) for safety_setting in (
            self.models[model]['options'].get('safety_settings')
        )
    ]
    return generative_models.GenerativeModel(
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


manager.LLMProviderManager.RegisterProvider(VertexAILLMProvider)
