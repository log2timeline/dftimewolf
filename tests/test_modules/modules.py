# -*- coding: utf-8 -*-
"""Contains dummy modules used in tests."""

from __future__ import unicode_literals

from dftimewolf.lib.module import BaseModule


class DummyModule1(BaseModule):
  """This is a dummy module."""

  def __init__(self, state):
    super(DummyModule1, self).__init__(state)
    self.name = 'Dummy1'

  def setup(self):  # pylint: disable=arguments-differ
    """Dummy setup function."""
    print(self.name + ' Setup!')

  def cleanup(self):
    pass

  def process(self):
    """Dummy Process function."""
    print(self.name + ' Process!')


class DummyModule2(BaseModule):
  """This is a dummy module."""

  def __init__(self, state):
    super(DummyModule2, self).__init__(state)
    self.name = 'Dummy2'

  def setup(self):  # pylint: disable=arguments-differ
    """Dummy setup function."""
    print(self.name + ' Setup!')

  def cleanup(self):
    pass

  def process(self):
    """Dummy Process function."""
    print(self.name + ' Process!')
