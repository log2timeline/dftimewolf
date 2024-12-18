"""Tests the Ollama processor module."""

import json
import unittest
from unittest import mock

import requests

from dftimewolf import config
from dftimewolf.lib.processors import llm_base
from dftimewolf.lib.processors.llmproviders import ollama


def get_mocked_response():
  response = mock.Mock(spec=requests.Response)
  response.status_code = 200
  response.json().return_value = { 'response': 'fake' }

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

  @mock.patch('requests.post', side_effect=get_mocked_response())
  def testGenerate(self, _mock_post):
    response = self.provider.Generate('blah', model='gemma')
    print(response)
    self.assertEqual(response, 'fake')


if __name__ == '__main__':
  unittest.main()
