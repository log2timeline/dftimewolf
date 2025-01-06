"""A ContainerManager class."""


import dataclasses
import threading
import typing
from typing import cast, Sequence, Type

from dftimewolf.lib.containers import interface



@dataclasses.dataclass
class _MODULE():
  name: str
  dependencies: list[str] = dataclasses.field(default_factory=list)
  storage: list[interface.AttributeContainer] = dataclasses.field(
      default_factory=list)
  completed: bool = False


class ContainerManager():
  """A ContainerManager.
  
  This ContainerManager handles container storage and delivery to modules.
  Modules can only receive containers from other modules that they directly
  depend on, according to the recipe (or themselves.) In this way, it implements
  a directional graph for container delivery.

  Attributes:
    _mutex: Practice safe container access.
    _modules: Container storage and dependency information.
  """

  def __init__(self):
    """Initialise a ContainerManager."""
    self._mutex = threading.Lock()
    self._modules: dict[str, _MODULE] = None

  def ParseRecipe(self, recipe: dict[str, typing.Any]) -> None:
    """Parses a recipe to build the dependency graph."""
    self._modules = {}

    for module in recipe.get('preflights', []) + recipe.get('modules', []):
      name = module.get('runtime_name', module.get('name', None))
      if not name:
        raise RuntimeError("Name not set for module in recipe")

      self._modules[name] = _MODULE(
          name=name, dependencies=module.get('wants', []) + [name])

  def StoreContainer(self,
                     source_module: str,
                     container: interface.AttributeContainer) -> None:
    """Adds a container to storage for later retrieval.

    Args:
      source_module: The module that generated the container.
      container: The container to store.
    """
    if not self._modules:
      raise RuntimeError("Container manager has not parsed a recipe yet")

    with self._mutex:
      self._modules[source_module].storage.append(container)


  def GetContainers(self,
                    requesting_module: str,
                    container_class: Type[interface.AttributeContainer],
                    metadata_filter_key: str | None = None,
                    metadata_filter_value: typing.Any = None
      ) -> Sequence[interface.AttributeContainer]:
    """Retrieves stored containers.
    
    A requesting module cannot retrieve containers that do not originate from a
    module that it depends on in the recipe or itself.
    
    Args:
      requesting_module: The module requesting the containers.
      container_class: The type of container to retrieve.
      metadata_filter_key: An optional metadata key to use to filter.
      metadata_filter_value: An optional metadata value to use to filter.

    Returns:
      A sequence of containers that match the various filters.
    """
    if not self._modules:
      raise RuntimeError("Container manager has not parsed a recipe yet")
    if bool(metadata_filter_key) ^ bool(metadata_filter_value):
      raise RuntimeError('Must specify both key and value for attribute filter')

    with self._mutex:
      ret_val = []

      for dependency in self._modules[requesting_module].dependencies:
        containers = self._modules[dependency].storage

        for c in containers:
          if (c.CONTAINER_TYPE != container_class.CONTAINER_TYPE or
              (metadata_filter_key and
              c.metadata.get(metadata_filter_key) != metadata_filter_value)):
            continue

          ret_val.append(c)

    return cast(Sequence[interface.AttributeContainer], ret_val)


  def CompleteModule(self, module_name: str) -> None:
    """Mark a module as completed in storage.

    Containers can consume large amounts of memory. Marking a module as
    completed tells the container manager that containers no longer needed can
    be removed from storage to free up that memory.

    Args:
      module_name: The module that has completed running.
    """
    with self._mutex:
      self._modules[module_name].completed = True

      # If all modules `module_name` is a dependency for are marked completed,
      # then containers it generated are no longer needed.
      for key in self._modules:
        if self._CheckDependenciesCompletion(key):
          for c in self._modules[key].storage:
            del c
          self._modules[key].storage = []

  def _CheckDependenciesCompletion(self, module_name: str) -> bool:
    """For a module, checks if other modules that depend on are complete."""
    for key in self._modules:
      if module_name in self._modules[key].dependencies:
        if not self._modules[key].completed:
          return False
    return True
