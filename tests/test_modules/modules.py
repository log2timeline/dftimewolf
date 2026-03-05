# -*- coding: utf-8 -*-
"""Contains dummy modules used in tests."""

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers


class DummyModule1(module.BaseModule):
  """This is a dummy module."""

  def __init__(self,
               name,
               container_manager_,
               cache_,
               telemetry_,
               publish_message_callback):
    self.runtime_value = None
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)

  def SetUp(self, runtime_value):  # pylint: disable=arguments-differ
    """Dummy setup function."""
    self.runtime_value = runtime_value
    self.RegisterStreamingCallback(callback=self.Callback,
                                   container_type=containers.Report)
    self.PublishMessage('Message from DummyModule1:SetUp')

  def Callback(self, _container):
    """Dummy callback that we just want to have called"""
    self.PublishMessage('Message from DummyModule1:Callback')

  def Process(self):
    """Dummy Process function."""
    self.LogTelemetry({'random_key1': 'random_value1'})
    self.PublishMessage('Message from DummyModule1:Process')


class DummyModule2(module.BaseModule):
  """This is a dummy module."""

  def __init__(self,
               name,
               container_manager_,
               cache_,
               telemetry_,
               publish_message_callback):
    self.runtime_value = None
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)

  def SetUp(self, runtime_value):  # pylint: disable=arguments-differ
    """Dummy setup function."""
    self.runtime_value = runtime_value
    self.PublishMessage('Message from DummyModule2:SetUp')

  def Process(self):
    """Dummy Process function."""
    self.LogTelemetry({'random_key2': 'random_value2'})
    self.PublishMessage('Message from DummyModule2:Process')


class DummyPreflightModule(module.PreflightModule):
  """Dummy preflight module."""

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

  def SetUp(self, args):  # pylint: disable=arguments-differ
    """Dummy Process function."""
    self.PublishMessage('Message from DummyPreflightModule:SetUp')

  def Process(self):
    """Dummy Process function."""
    self.PublishMessage('Message from DummyPreflightModule:Process')

  def CleanUp(self):
    """Dummy cleanup function."""
    self.PublishMessage('Message from DummyPreflightModule:CleanUp')
