# -*- coding: utf-8 -*-
"""Contains dummy modules used in thread aware tests."""

import time
from typing import TypeVar

from dftimewolf.lib import module
from dftimewolf.lib.containers import interface


_T = TypeVar("TestContainer")  # pylint: disable=typevar-name-mismatch


class TestContainer(interface.AttributeContainer):
  """Test attribute container."""

  CONTAINER_TYPE = 'test_container'

  def __init__(self, value: str) -> None:
    super(TestContainer, self).__init__()
    self.value = value

  def __eq__(self, other: _T) -> bool:
    return self.value == other.value

  def __str__(self) -> str:
    return self.value


class TestContainerTwo(interface.AttributeContainer):
  """Test attribute container."""

  CONTAINER_TYPE = 'test_container_two'

  def __init__(self, value: str) -> None:
    super(TestContainerTwo, self).__init__()
    self.value = value


class TestContainerThree(interface.AttributeContainer):
  """Test attribute container."""

  CONTAINER_TYPE = 'test_container_three'

  def __init__(self, value: str) -> None:
    super(TestContainerThree, self).__init__()
    self.value = value


class ContainerGeneratorModule(module.BaseModule):
  """This is a dummy module. Generates test containers."""

  def __init__(self,
               name,
               container_manager_,
               cache_,
               telemetry_,
               publish_message_callback):
    self.list = []
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)

  def SetUp(self, runtime_value=None): # pylint: disable=arguments-differ
    """Dummy setup function."""
    self.list = runtime_value.split(',')
    self.PublishMessage('Message from ContainerGeneratorModule:SetUp')

  def Process(self):
    """Dummy Process function."""
    for item in self.list:
      container = TestContainer(item)
      self.StoreContainer(container)
    container = TestContainerTwo(','.join(self.list))
    self.StoreContainer(container)
    self.PublishMessage('Message from ContainerGeneratorModule:Process')


class ThreadAwareConsumerModule(module.ThreadAwareModule):
  """This is a dummy Thread Aware Module. Consumes from
  ContainerGeneratorModule based on the number of containers generated."""

  def SetUp(self): # pylint: disable=arguments-differ
    """SetUp"""
    self.PublishMessage('Message from ThreadAwareConsumerModule:SetUp')

  def Process(self, container) -> None:
    """Process"""
    time.sleep(1)

    # This generates and stores a container in state.
    new_container = TestContainerThree('output ' + container.value)
    self.StoreContainer(new_container)

    # This modifies the container passed in as a parameter.
    container.value += ' appended'

    self.PublishMessage(
        f'Message from ThreadAwareConsumerModule:Process - {container.value}')

  def GetThreadOnContainerType(self):
    return TestContainer

  def GetThreadPoolSize(self):
    return 2

  def PreProcess(self) -> None:
    self.PublishMessage('Message from ThreadAwareConsumerModule:PreProcess')

  def PostProcess(self) -> None:
    self.PublishMessage('Message from ThreadAwareConsumerModule:PostProcess')


class Issue503Module(module.ThreadAwareModule):
  """This is a module for testing a certain pattern of container handling.

  As described by https://github.com/log2timeline/dftimewolf/issues/503 this
  module pops containers for input, and uses the same container type as output.
  """

  def __init__(self,
               name,
               container_manager_,
               cache_,
               telemetry_,
               publish_message_callback):
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)

  def SetUp(self): # pylint: disable=arguments-differ
    """SetUp"""
    self.PublishMessage('Message from Issue503Module:SetUp')

  def Process(self, container) -> None:
    """Process"""
    self.PublishMessage(
        f'Message from Issue503Module:Process - {container.value}')
    self.StoreContainer(TestContainer(container.value + " Processed"))

  def GetThreadOnContainerType(self):
    return TestContainer

  def GetThreadPoolSize(self):
    return 2

  def PreProcess(self) -> None:
    pass

  def PostProcess(self) -> None:
    pass

  def KeepThreadedContainersInState(self) -> bool:  # pylint: disable=arguments-differ
    return False
