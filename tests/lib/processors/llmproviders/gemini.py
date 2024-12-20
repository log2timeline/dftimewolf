# -*- coding: utf-8 -*-
"""Tests for Gemini LLMProvider."""

import json
import unittest
from unittest import mock

from dftimewolf import config
from dftimewolf.lib.processors.llmproviders import gemini


GEMINI_CONFIG = {
    'llm_providers': {
        'gemini': {
            'options': {
                'api_key': ''
            },
            'models': {
                'fake-gemini': {
                    'options': {
                        'generative_config': {
                            'temperature': 0.2,
                            'max_output_tokens': 8192,
                        },
                        'safety_settings': []
                    },
                    'tasks': [
                        'generate'
                    ]
                }
            }
        }
    }
}


class GeminiLLMProviderTest(unittest.TestCase):
  """Test for the GeminiLLMProvider."""

  @mock.patch('google.generativeai.configure')
  def test_configure_api_key(self, mock_gen_config):
    """Tests the configuration with an API key."""
    config.Config.LoadExtraData(json.dumps(
        {
            'llm_providers': {
                'gemini': {
                    'options': {
                        'api_key': 'test_api_key',
                    },
                    'models': {
                    }
                }
            }
        }
    ).encode('utf-8'))
    provider = gemini.GeminiLLMProvider()

    self.assertEqual(provider.options['api_key'], 'test_api_key')
    mock_gen_config.assert_called_with(api_key='test_api_key')

  @mock.patch.dict(
      gemini.os.environ,
      values={'GOOGLE_API_KEY': 'fake_env_key'},
      clear=True
  )
  @mock.patch('google.generativeai.configure')
  @mock.patch('google.generativeai.GenerativeModel', autospec=True)
  def test_generate(self, mock_gen_model, mock_gen_config):
    """Tests the generate method."""
    mock_gen_model.return_value.generate_content.return_value.text = (
        'test generate'
    )

    config.Config.LoadExtraData(json.dumps(GEMINI_CONFIG).encode('utf-8'))
    provider = gemini.GeminiLLMProvider()
    resp = provider.Generate(prompt='123', model='fake-gemini')

    self.assertEqual(resp, 'test generate')
    mock_gen_config.assert_called_once_with(api_key='fake_env_key')
    mock_gen_model.assert_called_once_with(
        model_name='fake-gemini',
        generation_config={
            'temperature': 0.2,
            'max_output_tokens': 8192,
        },
        safety_settings=[]
    )

  @mock.patch.dict(
    gemini.os.environ,
    values={'GOOGLE_API_KEY': 'fake_env_key'},
    clear=True
  )
  @mock.patch('google.generativeai.configure')
  @mock.patch('google.generativeai.GenerativeModel', autospec=True)
  def test_generate_with_history(self, mock_gen_model, mock_gen_config):
    """Tests the GenerateWithHistory method."""
    chat_instance = mock.MagicMock()
    mock_gen_model.return_value.start_chat.return_value = chat_instance
    chat_instance.send_message.return_value.text = 'test generate'
    config.Config.LoadExtraData(json.dumps(GEMINI_CONFIG).encode('utf-8'))

    provider = gemini.GeminiLLMProvider()
    resp = provider.GenerateWithHistory(prompt='123', model='fake-gemini')
    self.assertEqual(resp, 'test generate')
    mock_gen_config.assert_called_once_with(
        api_key='fake_env_key'
    )
    mock_gen_model.assert_called_once_with(
        model_name='fake-gemini',
        generation_config={
            'temperature': 0.2,
            'max_output_tokens': 8192,
        },
        safety_settings=[]
    )


if __name__ == '__main__':
  unittest.main()
