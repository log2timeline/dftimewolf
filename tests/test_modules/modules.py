# -*- coding: utf-8 -*-
"""Contains dummy modules used in tests."""

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers


class DummyModule1(module.BaseModule):
  """This is a dummy module."""

  def __init__(self, state):
    super(DummyModule1, self).__init__(state)
    self.name = 'Dummy1'

  def SetUp(self):  # pylint: disable=arguments-differ
    """Dummy setup function."""
    print(self.name + ' Setup!')
    self.state.RegisterStreamingCallback(self.Callback, containers.Report)

  def Callback(self, container):
    """Dummy callback that we just want to have called"""

  def Process(self):
    """Dummy Process function."""
    print(self.name + ' Process!')


class DummyModule2(module.BaseModule):
  """This is a dummy module."""

  def __init__(self, state):
    super(DummyModule2, self).__init__(state)
    self.name = 'Dummy2'

  def SetUp(self):  # pylint: disable=arguments-differ
    """Dummy setup function."""
    print(self.name + ' Setup!')

  def Process(self):
    """Dummy Process function."""
    print(self.name + ' Process!')

class DummyPreflightModule(module.PreflightModule):
  """Dummy preflight module."""

  def __init__(self, state):
    super(DummyPreflightModule, self).__init__(state)
    self.name = 'DummyPreflight'

  def SetUp(self, args):  # pylint: disable=arguments-differ
    """Dummy Process function."""
    print(self.name + ' Process!')

  def Process(self):
    """Dummy Process function."""
    print(self.name + ' Process!')
