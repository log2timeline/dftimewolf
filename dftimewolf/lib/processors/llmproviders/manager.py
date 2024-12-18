# -*- coding: utf-8 -*-
"""A manager for Large Language Model (LLM) providers."""

from typing import Dict, Iterable, Tuple, Type, List, Optional
from typing import overload
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from dftimewolf.lib.providers import interface


class LLMProviderManager:
  """The manager for LLM providers."""

  _provider_class_registry = {}

  @classmethod
  def GetProviders(cls) -> Iterable[Tuple[str, Type['interface.LLMProvider']]]:
    """Get all registered providers.

    Yields:
      A tuple of (provider_name, provider_class)
    """
    for provider_name, provider_class in cls._provider_class_registry.items():
      yield provider_name, provider_class

  @classmethod
  def GetProvider(cls, provider_name: str) -> type:
    """Get a provider by name.

    Args:
      provider_name: The name of the provider.

    Returns:
      The provider class.
    """
    try:
      provider_class = cls._provider_class_registry[provider_name.lower()]
    except KeyError as no_such_provider:
      raise KeyError(
          f"No such provider: {provider_name.lower()}"
      ) from no_such_provider
    return provider_class

  @classmethod
  def RegisterProvider(cls, provider_class: type) -> None:
    """Register a provider.

    Args:
      provider_class: The provider class to register.

    Raises:
      ValueError: If the provider is already registered.
    """
    provider_name = provider_class.NAME.lower()
    if provider_name in cls._provider_class_registry:
      raise ValueError(f"Provider {provider_class.NAME} already registered")
    cls._provider_class_registry[provider_name] = provider_class

  @classmethod
  def ClearRegistration(cls):
    """Clear all registered providers."""
    cls._provider_class_registry = {}
