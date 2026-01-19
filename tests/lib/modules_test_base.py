"""A base class for DFTW module testing."""

from typing import Sequence, Type

from absl.testing import parameterized

from dftimewolf import config
from dftimewolf.lib.containers import interface
from dftimewolf.lib.containers import manager as container_manager
from dftimewolf.lib import cache
from dftimewolf.lib import module
from unittest import mock


class ModuleTestBase(parameterized.TestCase):
  """A base class for DFTW module testing."""

  _module = None

  def __init__(self, *args, **kwargs):
    """Init."""
    super().__init__(*args, *kwargs)

  def _InitModule(self, test_module: type[module.BaseModule]):  # pylint: disable=arguments-differ
    """Initialises the module, the DFTW state and recipe for module testing."""
    self._cache = cache.DFTWCache()
    self._container_manager = container_manager.ContainerManager()
    self._container_manager.ParseRecipe(
        {'modules': [{'name': 'upstream'},
                     {'name': self._module.name, 'wants': ['upstream']},
                     {'name': 'downstream', 'wants': [self._module.name]}]}).
    self._telemetry = mock.MagicMock()

    self._module = test_module(name=self._module.name,
                               container_manager_=self._container_manager,
                               cache_=self._cache,
                               telemetry_=self._telemetry,
                               publish_message_callback=self._PublishMessage)

  def _ProcessModule(self):
    """Runs the process stage for the module."""
    if isinstance(self._module, module.ThreadAwareModule):
      self._module.PreProcess()
      containers = self._container_manager.GetContainers(
          self._module.GetThreadOnContainerType())
      for c in containers:
        self._module.Process(c)
      self._module.PostProcess()
    else:
      self._module.Process()

  def _AssertNoErrors(self):
    """Asserts that no errors have been generated."""
    # TODO - DO NOT SUBMIT

  def _UpstreamStoreContainer(self, container: interface.AttributeContainer):
    """Simulates the storing of a container from an upstream dependency."""
    self._container_manager.StoreContainer(container=container,
                                    source_module='upstream')

  def _DownstreamGetContainer(
      self, type_: Type[interface.AttributeContainer]
  ) -> Sequence[interface.AttributeContainer]:
    """Simulates the retreival of containers by a downstream dependency."""
    return self._container_manager.GetContainers(requesting_module='downstream',
                                                 container_class=type_)

  def _PublishMessage(self, source: str, message: str, is_error: bool = False) -> None:
    """Testing version of PublishMessage"""