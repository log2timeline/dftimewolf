# -*- coding: utf-8 -*-
"""Tests for the LLMProvider manager."""
import unittest

from dftimewolf.lib.processors.llmproviders import interface
from dftimewolf.lib.processors.llmproviders import manager


class FakeLLMProvider(interface.LLMProvider):
  """Fake LLMProvider for testing."""
  NAME = 'test'

  def Generate(self, prompt: str, model: str, **kwargs) -> str:
    return 'test'

  def GenerateWithHistory(self, prompt: str, model: str, **kwargs) -> str:
    return 'test'


class LLMProviderManagerTests(unittest.TestCase):
  """Unit tests for the LLMProviderManager."""

  def testManager(self):
    """Tests the LLMProviderManager."""
    with self.subTest('not registered'):
      with self.assertRaisesRegex(KeyError, 'No such provider'):
        manager.LLMProviderManager.GetProvider('test')

    with self.subTest('register'):
      manager.LLMProviderManager.RegisterProvider(FakeLLMProvider)
      self.assertEqual(
          len(manager.LLMProviderManager._provider_class_registry),  # pylint: disable=protected-access
          1
      )

    with self.subTest('already registered'):
      with self.assertRaisesRegex(ValueError, 'already registered'):
        manager.LLMProviderManager.RegisterProvider(FakeLLMProvider)

    with self.subTest('get'):
      provider = manager.LLMProviderManager.GetProvider('test')
      self.assertEqual(provider, FakeLLMProvider)

    with self.subTest('list'):
      providers = list(manager.LLMProviderManager.GetProviders())
      self.assertEqual(len(providers), 1)
      self.assertEqual(providers[0], ('test', FakeLLMProvider))

    with self.subTest('clear'):
      manager.LLMProviderManager.ClearRegistration()
      self.assertEqual(
          len(manager.LLMProviderManager._provider_class_registry),  # pylint: disable=protected-access
          0
      )


if __name__ == '__main__':
  unittest.main()
