'''Tests for VertexAI LLMProvider.'''

import json
import unittest
from unittest import mock

from dftimewolf import config
from dftimewolf.lib.processors.llmproviders import vertex_ai


VERTEX_AI_CONFIG = {
    'llm_providers': {
        'vertexai': {
            'options': {
                'project_id': 'myproject',
                'region': 'australia-southeast2'
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


class VertexAILLMProviderTest(unittest.TestCase):
  """Test for the VertexAILLMProvider."""

  @mock.patch('vertexai.init')
  @mock.patch(
      'google.oauth2.service_account.Credentials.from_service_account_info')
  def test_configure_api_key(self, mock_info, mock_gen_config):
    """Tests the configuration with an API key."""
    mock_service_account = mock.MagicMock()
    mock_info.return_value = mock_service_account
    config.Config.LoadExtraData(json.dumps(
        {
            'llm_providers': {
                'vertexai': {
                    'options': {
                        'api_key': 'test_api_key',
                        'project_id': 'myproject',
                        'region': 'australia-southeast2',
                        'sa_path': 'fake_path'
                    },
                    'models': {
                    }
                }
            }
        }
    ).encode('utf-8'))
    with mock.patch(
        'builtins.open',
        new=mock.mock_open(read_data='{"service key": [1]}')) as _:
      provider = vertex_ai.VertexAILLMProvider()

    mock_info.assert_called_with({"service key": [1]})
    self.assertEqual(provider.options['api_key'], 'test_api_key')
    mock_gen_config.assert_called_with(
        credentials=mock_service_account,
        api_key='test_api_key',
        project='myproject',
        location='australia-southeast2'
    )

  @mock.patch.dict(
      vertex_ai.os.environ,
      values={'HOME': 'fake_home'},
      clear=True)
  @mock.patch('vertexai.init')
  @mock.patch('os.path.exists')
  def test_configure_home(self, mock_exists, mock_gen_config):
    """Tests the configuration with a environment variable."""
    mock_exists.return_value = True
    config.Config.LoadExtraData(json.dumps(
        {'llm_providers': {'vertexai': {'options': {},'models': {}}}}
    ).encode('utf-8'))
    provider = vertex_ai.VertexAILLMProvider()
    self.assertIsNotNone(provider)
    mock_gen_config.assert_called_with(
        api_key=None, project=None, location=None
    )

  @mock.patch.dict(
      vertex_ai.os.environ,
      values={'GOOGLE_APPLICATION_CREDENTIALS': 'fake_env_key'},
      clear=True)
  @mock.patch('vertexai.init')
  def test_configure_ac(self, mock_gen_config):
    """Tests the configuration error."""
    config.Config.LoadExtraData(json.dumps(
        {'llm_providers': {'vertexai': {'options': {},'models': {}}}}
    ).encode('utf-8'))
    provider = vertex_ai.VertexAILLMProvider()
    self.assertIsNotNone(provider)
    mock_gen_config.assert_called_with(
        api_key=None, project=None, location=None
    )

  @mock.patch.dict(
      vertex_ai.os.environ,
      values={'GOOGLE_APPLICATION_CREDENTIALS': 'fake_env_key'},
      clear=True)
  @mock.patch('vertexai.init')
  @mock.patch('vertexai.generative_models.GenerativeModel', autospec=True)
  def test_generate(self, mock_gen_model, mock_gen_config):
    """Tests the generate method."""
    mock_gen_model.return_value.generate_content.return_value.text = (
        'test generate'
    )

    config.Config.LoadExtraData(json.dumps(VERTEX_AI_CONFIG).encode('utf-8'))
    provider = vertex_ai.VertexAILLMProvider()
    resp = provider.Generate(prompt='123', model='fake-gemini')

    self.assertEqual(resp, 'test generate')
    mock_gen_config.assert_called_once_with(
        api_key=None, project='myproject', location='australia-southeast2'
    )
    mock_gen_model.assert_called_once_with(
        model_name='models/fake-gemini',
        generation_config={
            'temperature': 0.2,
            'max_output_tokens': 8192,
        },
        safety_settings=[]
    )

  @mock.patch.dict(
      vertex_ai.os.environ,
      values={'GOOGLE_APPLICATION_CREDENTIALS': 'fake_env_key'},
      clear=True)
  @mock.patch('vertexai.init')
  @mock.patch('vertexai.generative_models.GenerativeModel', autospec=True)
  def test_generate_with_history(self, mock_gen_model, mock_gen_config):
    """Tests the GenerateWithHistory method."""
    chat_instance = mock.MagicMock()
    mock_gen_model.return_value.start_chat.return_value = chat_instance
    chat_instance.send_message.return_value.text = 'test generate'
    config.Config.LoadExtraData(json.dumps(VERTEX_AI_CONFIG).encode('utf-8'))

    provider = vertex_ai.VertexAILLMProvider()
    resp = provider.GenerateWithHistory(prompt='123', model='fake-gemini')
    self.assertEqual(resp, 'test generate')
    mock_gen_config.assert_called_once_with(
        api_key=None, project='myproject', location='australia-southeast2'
    )
    mock_gen_model.assert_called_once_with(
        model_name='models/fake-gemini',
        generation_config={
            'temperature': 0.2,
            'max_output_tokens': 8192,
        },
        safety_settings=[]
    )


if __name__ == '__main__':
  unittest.main()
