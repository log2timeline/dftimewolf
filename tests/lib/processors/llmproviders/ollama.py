"""Tests the Ollama LLMprocessor module."""

import json
import unittest
from unittest import mock

import requests

from dftimewolf import config
from dftimewolf.lib.processors.llmproviders import ollama


def get_mocked_response(*args, **kwargs):
  response = mock.MagicMock(spec=requests.Response)
  response.status_code = 200
  if args[0].endswith('generate'):
    prompt = kwargs['json']['prompt']
    response.json.return_value = {
      'response': f'generate response to {prompt}'}
  elif args[0].endswith('chat'):
    prompt = kwargs['json']['messages'][-1]['content']
    response.json.return_value = {
      'message': {
        'role': 'assistant', 'content': f'chat response to {prompt}'
      }
    }
  return response


class OllamaLLMProviderTest(unittest.TestCase):
  """Tests for the OllamaLLMProvider."""

  def setUp(self):
    config.Config.LoadExtraData(json.dumps(
        {
            "llm_providers": {
              "ollama": {
                "options": {
                  "server_url": "http://fake.ollama:11434"
                },
                "models": {
                  "gemma": {
                    "options": {
                    },
                    "tasks": ["test_task"]
                  }
                }
              }
          }
      }
    ))
    self.provider = ollama.OllamaLLMProvider()

  def tearDown(self):
    config.Config.ClearExtra()

  def testInit(self):
    """Tests the provider is initialized."""
    self.assertIsNotNone(self.provider)
    self.assertEqual(self.provider.chat_history, [])

  @mock.patch('requests.post', side_effect=get_mocked_response)
  def testGenerate(self, mock_post):
    response = self.provider.Generate('blah', model='gemma')
    self.assertEqual(response, 'generate response to blah')
    mock_post.assert_called_with(
        'http://fake.ollama:11434/api/generate',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        json={
            'prompt': 'blah',
            'model': 'gemma',
            'stream': False,
            'options': {
                'temperature': 0.2,
                'num_predict': 8192
            }
        },
        allow_redirects=True
    )

  @mock.patch('requests.post', side_effect=get_mocked_response)
  def testGenerateWithHistory(self, mock_post):
    response_first = self.provider.GenerateWithHistory('who are you?', model='gemma')
    self.assertEqual(response_first, 'chat response to who are you?')
    response_second = self.provider.GenerateWithHistory('why?', model='gemma')
    self.assertEqual(response_second, 'chat response to why?')
    mock_post.assert_called_with(
        'http://fake.ollama:11434/api/chat',
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        json={
          'messages': [
              {
                  'role': 'user',
                  'content': 'who are you?'
              },
              {
                  'role': 'assistant',
                  'content': 'chat response to who are you?'
              },
              {
                  'role': 'user',
                  'content': 'why?'
              },
          ],
          'model': 'gemma',
          'stream': False,
          'options': {
            'temperature': 0.2,
            'num_predict': 8192
          }
        },
        allow_redirects=True
    )
    self.assertEqual(len(self.provider.chat_history), 4)
    self.assertEqual(
        self.provider.chat_history[3],
        {
            'role': 'assistant',
            'content': 'chat response to why?'
        }
    )


if __name__ == '__main__':
  unittest.main()
