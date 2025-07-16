"""A ContainerManager class."""


from concurrent import futures
import dataclasses
import logging
import threading
from typing import Any, cast, Sequence, Type, TypeVar, Callable

from dftimewolf.lib.containers import interface

# pylint: disable=line-too-long

T = TypeVar("T", bound="interface.AttributeContainer")


@dataclasses.dataclass
class _MODULE():
  """A helper class for tracking module storage and dependency info.

  Attributes:
    name:  The module name.
    dependencies: A list of modules that this module depends on.
    storage: A dict, keyed by container type, of:
        A tuple of:
            The container (a ref)
            The originating module
    callback_map: A dict, keyed by container type of callback methods
  """
  name: str
  dependencies: list[str] = dataclasses.field(default_factory=list)
  storage: dict[str, list[tuple[interface.AttributeContainer, str]]] = dataclasses.field(default_factory=dict)
  callback_map: dict[str, list[Callable[[interface.AttributeContainer], None]]] = dataclasses.field(default_factory=dict)

  def RegisterCallback(
      self, container_type: str, callback: Callable[[interface.AttributeContainer], None]) -> None:
    """Registers a callback for the module for a given container type."""
    if container_type not in self.callback_map:
      self.callback_map[container_type] = []
    self.callback_map[container_type].append(callback)

  def GetCallbacksForContainer(
      self, container_type: str) -> list[Callable[[interface.AttributeContainer], None]]:
    """Returns all callbacks for the module, for a given container type."""
    return self.callback_map.get(container_type, [])


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

  def __init__(self, logger: logging.Logger) -> None:
    """Initialise a ContainerManager."""
    self._logger = logger
    self._mutex = threading.Lock()
    self._modules: dict[str, _MODULE] = {}
    self._callback_pool = futures.ThreadPoolExecutor()

  def __del__(self) -> None:
    """Clean up the ContainerManager."""
    self.WaitForCallbackCompletion()

  def ParseRecipe(self, recipe: dict[str, Any]) -> None:
    """Parses a recipe to build the dependency graph.

    Args:
      recipe: The recipe dict, that comes from the recipe manager class.

    Raises:
      RuntimeError: If there is an error in the recipe definition.
    """
    with self._mutex:
      self._modules = {}

      for module in recipe.get('preflights', []) + recipe.get('modules', []):
        name = module.get('runtime_name', module.get('name', None))
        if not name:
          raise RuntimeError("Name not set for module in recipe")

        self._modules[name] = _MODULE(name=name, dependencies=module.get('wants', []) + [name])

  def StoreContainer(self,
                     source_module: str,
                     container: interface.AttributeContainer,
                     for_self_only: bool=False) -> None:
    """Adds a container to storage for later retrieval.

    This method will also invoke any applicable callbacks that have been
    registered (callbacks for the same module are never invoked to prevent
    infinite recursion.)

    Args:
      source_module: The module that generated the container.
      container: The container to store.
      for_self_only: True if the container should only be available to the same
          module that stored it.

    Raises:
      RuntimeError: If the manager has not been configured with a recipe yet.
    """
    if not self._modules:
      raise RuntimeError("Container manager has not parsed a recipe yet")

    with self._mutex:
      self._logger.debug(f'{source_module} is storing a {container.CONTAINER_TYPE} container: {str(container)}')

      for _, module in self._modules.items():
        if source_module in module.dependencies:
          if for_self_only and module.name != source_module:
            continue
          callbacks = module.GetCallbacksForContainer(container.CONTAINER_TYPE)
          if callbacks and module.name != source_module:
            # This module has registered callbacks - Use those, rather than storing
            for callback in callbacks:
              self._logger.debug('Executing callback for %s with container %s', module.name, str(container))
              self._callback_pool.submit(callback, container)
          else:
            if container.CONTAINER_TYPE not in module.storage:
              module.storage[container.CONTAINER_TYPE] = []

            # If the container to add exists already in the state, don't add it again
            if container in [c for c, _ in module.storage[container.CONTAINER_TYPE]]:
              continue
            module.storage[container.CONTAINER_TYPE].append((container, source_module))

  def GetContainers(self,
                    requesting_module: str,
                    container_class: Type[T],
                    pop: bool = False,
                    metadata_filter_key: str | None = None,
                    metadata_filter_value: Any = None
      ) -> Sequence[T]:
    """Retrieves stored containers.
    
    A requesting module cannot retrieve containers that do not originate from a
    module that it depends on in the recipe or itself.
    
    Args:
      requesting_module: The module requesting the containers.
      container_class: The type of container to retrieve.
      pop: True if the returned containers should be removed from the state.
          False otherwise. Ignored if the source and requesting module do not
          match. That is, a module can only pop containers it has stored.
      metadata_filter_key: An optional metadata key to use to filter.
      metadata_filter_value: An optional metadata value to use to filter.

    Returns:
      A sequence of containers that match the various filters.

    Raises:
      RuntimeError: If the manager has not been configured with a recipe yet; or
          if only one of metadata_filter_(key|value) is specified.
    """
    if not self._modules:
      raise RuntimeError('Container manager has not parsed a recipe yet')
    if bool(metadata_filter_key) ^ bool(metadata_filter_value):
      raise RuntimeError('Must specify both key and value for attribute filter')

    with self._mutex:
      collected_containers: list[tuple[interface.AttributeContainer, str]] = []

      for container, origin in self._modules[requesting_module].storage.get(container_class.CONTAINER_TYPE, []):
        if (metadata_filter_key and container.metadata.get(metadata_filter_key) != metadata_filter_value):
          continue
        collected_containers.append((container, origin))

      if pop:
        self._RemoveStoredContainers([c for c, _ in collected_containers], requesting_module)

    self._logger.debug(f'{requesting_module} is retrieving {len(collected_containers)} '
                       f'{container_class.CONTAINER_TYPE} containers (pop == {pop})')
    for container, origin in collected_containers:
      self._logger.debug(f'  * {str(container)} - origin: {origin}')

    return cast(Sequence[T], [c for c, _ in collected_containers])

  def CompleteModule(self, module_name: str) -> None:
    """Mark a module as completed in storage.

    Containers can consume large amounts of memory. Marking a module as
    completed tells the container manager that containers no longer needed can
    be removed from storage to free up that memory.

    Args:
      module_name: The module that has completed running.

    Raises:
      RuntimeError: If the manager has not been configured with a recipe yet.
    """
    if not self._modules:
      raise RuntimeError("Container manager has not parsed a recipe yet")

    with self._mutex:
      self._modules[module_name].storage = {}

  def RegisterStreamingCallback(
      self,
      module_name: str,
      container_type: Type[T],
      callback: Callable[[interface.AttributeContainer], None]) -> None:
    """Registers a container streaming callback for a module and container type.
    
    Args:
      module_name: The module name registering the callback
      container_type: The container type to stream
      callback: The function to call with containers
    """
    if not self._modules:
      raise RuntimeError('Container manager has not parsed a recipe yet')
    if module_name not in self._modules:
      raise RuntimeError('Registering a callback for a non-existent module')

    self._modules[module_name].RegisterCallback(container_type.CONTAINER_TYPE, callback)

  def WaitForCallbackCompletion(self) -> None:
    """Waits for all scheduled callbacks to be completed."""
    self._callback_pool.shutdown(wait=True)

  def _RemoveStoredContainers(self, containers: list[T], requesting_module: str) -> None:
    """Removes containers from storage.

    A module can only remove containers that it has stored.

    Args:
      containers: The list of containers that to potentially remove from storage
      requesting_module: The module making the pop request
    """
    if not containers:
      return

    # All the containers will be the same type
    container_type = containers[0].CONTAINER_TYPE
    ids = [id(c) for c in containers]

    for _, module in self._modules.items():
      filtered = []
      for c, origin in module.storage.get(container_type, []):
        if not (origin == requesting_module and id(c) in ids):
          filtered.append((c, origin))
      module.storage[container_type] = filtered

  def __str__(self) -> str:
    """Used for debugging."""
    lines = []

    for name, module in self._modules.items():
      lines.append(f'Module: {name}')
      lines.append('  Dependencies:')
      lines.append(f'    {", ".join(module.dependencies)}')
      lines.append('  Callbacks:')
      for type_, cb in module.callback_map.items():
        lines.append(f'    {type_}:{cb}')
      lines.append('  Containers:')
      for type_ in module.storage.keys():
        lines.append(f'    {type_}')
        for c, origin in module.storage[type_]:
          lines.append(f'      {origin}:{c}')
      lines.append('')

    return '\n'.join(lines)
