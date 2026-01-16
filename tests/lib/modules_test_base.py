"""A base class for DFTW module testing."""

from typing import Sequence, Type

from absl.testing import parameterized

from dftimewolf import config
from dftimewolf.lib.containers import interface
from dftimewolf.lib import state
from dftimewolf.lib import module
from unittest import mock


class ModuleTestBase(parameterized.TestCase):
  """A base class for DFTW module testing."""

  _module = None

  def __init__(self, *args, **kwargs):
    """Init."""
    super().__init__(*args, *kwargs)
    self._test_state: state.DFTimewolfState = None

  def _InitModule(self, test_module: type[module.BaseModule]):  # pylint: disable=arguments-differ
    """Initialises the module, the DFTW state and recipe for module testing."""
    self._test_state = state.DFTimewolfState(config.Config,
                                             telemetry=mock.MagicMock())
    self._module = test_module(self._test_state)
    self._test_state._container_manager.ParseRecipe(  # pylint: disable=protected-access
        {'modules': [{'name': 'upstream'},
                     {'name': self._module.name, 'wants': ['upstream']},
                     {'name': 'downstream', 'wants': [self._module.name]}]})

  def _ProcessModule(self):
    """Runs the process stage for the module."""
    if isinstance(self._module, module.ThreadAwareModule):
      self._module.PreProcess()
      containers = self._module.GetContainers(
          self._module.GetThreadOnContainerType())
      for c in containers:
        self._module.Process(c)
      self._module.PostProcess()
    else:
      self._module.Process()

  def _AssertNoErrors(self):
    """Asserts that no errors have been generated."""
    self.assertEqual([], self._module.state.errors)

  def _UpstreamStoreContainer(self, container: interface.AttributeContainer):
    """Simulates the storing of a container from an upstream dependency."""
    self._test_state.StoreContainer(container=container,
                                    source_module='upstream')

  def _DownstreamGetContainer(
      self, type_: Type[interface.AttributeContainer]
  ) -> Sequence[interface.AttributeContainer]:
    """Simulates the retreival of containers by a downstream dependency."""
    return self._test_state.GetContainers(requesting_module='downstream',
                                          container_class=type_)
