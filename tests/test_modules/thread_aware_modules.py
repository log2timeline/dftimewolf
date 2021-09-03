# -*- coding: utf-8 -*-
"""Contains dummy modules used in thread aware tests."""

from typing import Dict, Any
import time

from dftimewolf.lib import module
from dftimewolf.lib.containers import interface

class TestContainer(interface.AttributeContainer):
  """Test attribute container."""

  CONTAINER_TYPE = 'test_container'

  def __init__(self, value: str) -> None:
    super(TestContainer, self).__init__()
    self.value = value

class TestContainerTwo(interface.AttributeContainer):
  """Test attribute container."""

  CONTAINER_TYPE = 'test_container_two'

  def __init__(self, value: str) -> None:
    super(TestContainerTwo, self).__init__()
    self.value = value


class ContainerGeneratorModule(module.BaseModule):
  """This is a dummy module. Generates test containers."""

  def __init__(self, state, name=None):
    self.list = []
    super(ContainerGeneratorModule, self).__init__(state, name)

  def SetUp(self, runtime_value=None): # pylint: disable=arguments-differ
    """Dummy setup function."""
    print(self.name + ' Setup!')
    self.list = runtime_value.split(',')

  def Process(self):
    """Dummy Process function."""
    print(self.name + ' Process!')
    for item in self.list:
      container = TestContainer(item)
      self.state.StoreContainer(container)
    container = TestContainerTwo(','.join(self.list))
    self.state.StoreContainer(container)

class ThreadAwareConsumerModule(module.ThreadAwareModule):
  """This is a dummy Thread Aware Module. Consumes from
  ContainerGeneratorModule based on the number of containers generated."""

  def SetUp(self): # pylint: disable=arguments-differ
    """SetUp"""
    print(self.name + ' SetUp!')

  def Process(self) -> None:
    """Process"""
    print(self.name + ' Process!')

    time.sleep(1)

    for container in self.GetContainers(TestContainer):
      container.value += ' appended'
    self.GetContainers(TestContainerTwo)[0].value += ' appended'

  @staticmethod
  def GetThreadOnContainerType():
    return TestContainer

  @staticmethod
  def GetThreadPoolSize():
    return 2

  @staticmethod
  def StaticPreSetUp() -> None:
    print("ThreadAwareConsumerModule Static Pre Set Up")

  @staticmethod
  def StaticPostSetUp() -> None:
    print("ThreadAwareConsumerModule Static Post Set Up")

  @staticmethod
  def StaticPreProcess() -> None:
    print("ThreadAwareConsumerModule Static Pre Process")

  @staticmethod
  def StaticPostProcess() -> None:
    print("ThreadAwareConsumerModule Static Post Process")
