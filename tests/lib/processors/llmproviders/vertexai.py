'''Tests for VertexAI LLMProvider.'''

import json
import os
import unittest
from unittest import mock

from google.generativeai import protos as genai_types
from google.generativeai import generative_models
from dftimewolf import config
from dftimewolf.lib.processors.llmproviders import vertexai


GENAI_CONFIG = {
    'llm_providers': {
        'vertexai': {
            'options': {
                'project_id': 'myproject',
                'zone': 'fake_zone'
            },
            'models': {
                'fake-gemini': {
                    'options': {
                        'generative_config': {
                            'temperature': 0.2,
                            'max_output_tokens': 8192,
                        },
                        'safety_settings': [
                            {
                              'category': 'example_category',
                              'threshold': 'BLOCK_NONE',
                            }
                        ]
                    },
                    'tasks': [
                        'generate'
                    ]
                }
            }
        }
    }
}


class VertexAILLMProviderTest(unittest.TestCase):
  """Test for the VertexAILLMProvider."""

  @mock.patch('google.generativeai.configure')
  def test_configure_api_key(self, mock_gen_config):
    config.Config.LoadExtraData(json.dumps(
        {
            'llm_providers': {
                'vertexai': {
                    'options': {
                        'api_key': 'test_api_key'
                    },
                    'models': {
                    }
                }
            }
        }
    ))
    provider = vertexai.VertexAILLMProvider()

    self.assertEqual(provider.options['api_key'], 'test_api_key')
    mock_gen_config.assert_called_with(api_key='test_api_key')

  @mock.patch('google.generativeai.configure')
  def test_configure_project_id_zone(self, mock_gen_config):
    config.Config.LoadExtraData(json.dumps(
        {
            'llm_providers': {
                'vertexai': {
                    'options': {
                        'project_id': 'myproject',
                        'zone': 'fake_zone'
                    },
                    'models': {
                    }
                }
            }
        }
    ))
    provider = vertexai.VertexAILLMProvider()

    self.assertEqual(provider.options['project_id'], 'myproject')
    self.assertEqual(provider.options['zone'], 'fake_zone')
    mock_gen_config.assert_called_with(
        project_id='myproject', zone='fake_zone'
    )

  @mock.patch.dict(vertexai.os.environ, {'GOOGLE_API_KEY': 'fake_env_key'}, clear=True)
  @mock.patch('google.generativeai.configure')
  def test_configure_env(self, mock_gen_config):
    config.Config.LoadExtraData(json.dumps(
        {'llm_providers': {'vertexai': {'options': {},'models': {}}}}
    ))
    provider = vertexai.VertexAILLMProvider()
    mock_gen_config.assert_called_with(api_key='fake_env_key')

  @mock.patch('google.generativeai.configure')
  def test_configure_empty(self, mock_gen_config):
    config.Config.LoadExtraData(json.dumps(
        {'llm_providers': {'vertexai': {'options': {},'models': {}}}}
    ))
    with self.assertRaisesRegex(
        RuntimeError, 'API key or project_id/zone must be set'):
      provider = vertexai.VertexAILLMProvider()


  @mock.patch('google.generativeai.configure')
  @mock.patch('google.generativeai.GenerativeModel', autospec=True)
  def test_generate(self, mock_gen_model, mock_gen_config):
    mock_gen_model.return_value.generate_content.return_value.text = 'test generate'

    config.Config.LoadExtraData(json.dumps(GENAI_CONFIG))
    provider = vertexai.VertexAILLMProvider()
    resp = provider.Generate(prompt='123', model='fake-gemini')

    self.assertEqual(resp, 'test generate')
    mock_gen_config.assert_called_once_with(project_id='myproject', zone='fake_zone')
    mock_gen_model.assert_called_once_with(
        model_name='models/fake-gemini',
        generation_config={
            'temperature': 0.2,
            'max_output_tokens': 8192,
        },
        safety_settings=[
            {
                'category': 'example_category',
                'threshold': 'BLOCK_NONE',
            }
        ]
    )

  @mock.patch('google.generativeai.configure')
  @mock.patch('google.generativeai.GenerativeModel', autospec=True)
  def test_generate_with_history(self, mock_gen_model, mock_gen_config):
    chat_instance = mock.MagicMock()
    mock_gen_model.return_value.start_chat.return_value = chat_instance
    chat_instance.send_message.return_value.text = 'test generate'
    config.Config.LoadExtraData(json.dumps(GENAI_CONFIG))

    provider = vertexai.VertexAILLMProvider()
    resp = provider.GenerateWithHistory(prompt='123', model='fake-gemini')
    self.assertEqual(resp, 'test generate')
    mock_gen_config.assert_called_once_with(project_id='myproject', zone='fake_zone')
    mock_gen_model.assert_called_once_with(
        model_name='models/fake-gemini',
        generation_config={
            'temperature': 0.2,
            'max_output_tokens': 8192,
        },
        safety_settings=[
            {
                'category': 'example_category',
                'threshold': 'BLOCK_NONE',
            }
        ]
    )


if __name__ == '__main__':
  unittest.main()
