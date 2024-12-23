# -*- coding: utf-8 -*-
"""A manager for Large Language Model (LLM) providers."""

from typing import Iterable, Type
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from dftimewolf.lib.processors.llmproviders import interface


class LLMProviderManager:
  """The manager for LLM providers."""

  _provider_class_registry: dict[str, Type['interface.LLMProvider']] = {}

  @classmethod
  def GetProviders(cls) -> Iterable[tuple[str, Type['interface.LLMProvider']]]:
    """Get all registered providers.

    Yields:
      A tuple of (provider_name, provider_class)
    """
    for provider_name, provider_class in cls._provider_class_registry.items():
      yield provider_name, provider_class

  @classmethod
  def GetProvider(cls, provider_name: str) -> Type['interface.LLMProvider']:
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
  def RegisterProvider(
      cls,
      provider_class: Type['interface.LLMProvider']
  ) -> None:
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
  def ClearRegistration(cls) -> None:
    """Clear all registered providers."""
    cls._provider_class_registry = {}
