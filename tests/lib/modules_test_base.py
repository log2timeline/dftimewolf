"""A base class for DFTW module testing."""

from absl.testing import parameterized

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib import module


class ModuleTestBase(parameterized.TestCase):
  """A base class for DFTW module testing."""

  _test_state = None
  _module = None

  def _InitModule(self, test_module: type[module.BaseModule]):  # pylint: disable=arguments-differ
    """Initialises the module, the DFTW state and recipe for module testing."""
    self._test_state = state.DFTimewolfState(config.Config)
    self._module = test_module(self._test_state)
    self._test_state._container_manager.ParseRecipe(  # pylint: disable=protected-access
        {'modules': [{'name': self._module.name}]})

  def _ProcessModule(self):
    """Runs the process stage for the module."""
    if isinstance(self._module, module.ThreadAwareModule):
      containers = self._module.GetContainers(
          self._module.GetThreadOnContainerType())
      self._module.PreProcess()
      for c in containers:
        self._module.Process(c)
      self._module.PostProcess()
    else:
      self._module.Process()
