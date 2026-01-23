"""A simple cache by name."""

import threading
import typing


# pylint: disable=line-too-long


_RECIPE_NAME_CACHE_KEY = 'recipe_name'
_CLI_ARGS_CACHE_KEY = 'cli_args'


class DFTWCache:
  """A simple cache by name.

  A replacement for the legacy state.py based cache.
  """

  def __init__(self):
    """Init."""
    self._cache: dict[str, typing.Any] = {}
    self._mutex = threading.Lock()

  def AddToCache(self, name: str, value: typing.Any) -> None:
    """Thread-safe method to add data to the state's cache.

    If the cached item is already in the cache it will be overwritten with the
    new value.

    Args:
      name (str): string with the name of the cache variable.
      value (object): the value that will be stored in the cache.
    """
    with self._mutex:
      self._cache[name] = value

  def GetFromCache(self, name: str, default_value: typing.Any = None) -> typing.Any:
    """Thread-safe method to get data from the state's cache.

    Args:
      name (str): string with the name of the cache variable.
      default_value (object): the value that will be returned if the item does
          not exist in the cache. Optional argumentand defaults to None.

    Returns:
      object: object from the cache that corresponds to the name, or the value
          of "default_value" if the cache does not contain the variable.
    """
    with self._mutex:
      return self._cache.get(name, default_value)

  def SetRecipeName(self, recipe_name: str) -> None:
    """Dedicated method for setting the name of the current recipe."""
    self.AddToCache(_RECIPE_NAME_CACHE_KEY, recipe_name)

  def GetRecipeName(self) -> str:
    """Dedicated method for fetching the name of the current recipe."""
    return self.GetFromCache(_RECIPE_NAME_CACHE_KEY)

  def SetCLIArgs(self, args: str) -> None:
    """Dedicated method for setting the CLI arguments for this execution."""
    self.AddToCache(_CLI_ARGS_CACHE_KEY, args)

  def GetCLIArgs(self) -> str:
    """Dedicated method for getting the CLI arguments for this execution."""
    return self.GetFromCache(_CLI_ARGS_CACHE_KEY)
