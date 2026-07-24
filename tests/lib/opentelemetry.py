# -*- coding: utf-8 -*-
"""Tests for OpenTelemetry integration."""

import os
from typing import Any, cast
import unittest
from unittest import mock

from dftimewolf.lib import module
from dftimewolf.lib.opentelemetry import (
    SetupOpenTelemetry,
    add_attribute_to_current_span,
    add_event_to_current_span,
    get_current_span,
    safe_telemetry_call,
    start_span,
)


try:
  import opentelemetry.sdk.trace  # type: ignore
  import opentelemetry.exporter.otlp.proto.http.trace_exporter  # type: ignore
  HAS_OTEL_SDK = True
except (ImportError, ModuleNotFoundError):
  HAS_OTEL_SDK = False


class OpenTelemetryTest(unittest.TestCase):
  """Tests for OpenTelemetry setup and helper functions."""

  def setUp(self):
    super().setUp()
    # Save environment state
    self._orig_otel_mode = os.environ.get('DFTIMEWOLF_OTEL_MODE')

  def tearDown(self):
    super().tearDown()
    # Restore environment state
    if self._orig_otel_mode is not None:
      os.environ['DFTIMEWOLF_OTEL_MODE'] = self._orig_otel_mode
    elif 'DFTIMEWOLF_OTEL_MODE' in os.environ:
      del os.environ['DFTIMEWOLF_OTEL_MODE']

  @mock.patch('dftimewolf.config.Config.GetExtra')
  def testSetupOpenTelemetryDisabled(self, mock_get_extra):
    """Tests that SetupOpenTelemetry handles disabled config gracefully."""
    mock_get_extra.return_value = {'type': 'google_cloud_spanner', 'config': {'opentelemetry': {'enabled': False}}}
    SetupOpenTelemetry()

  @mock.patch('dftimewolf.config.Config.GetExtra')
  def testSetupOpenTelemetryInvalidMode(self, mock_get_extra):
    """Tests that SetupOpenTelemetry handles unsupported mode gracefully."""
    mock_get_extra.return_value = {'type': 'google_cloud_spanner', 'config': {'opentelemetry': {'enabled': True, 'mode': 'unsupported_mode'}}}
    SetupOpenTelemetry()

  def testSetupOpenTelemetryCustomTracerProvider(self):
    """Tests initializing with a custom tracer provider."""
    mock_provider = mock.MagicMock()
    with mock.patch('opentelemetry.trace.set_tracer_provider') as mock_set:
      SetupOpenTelemetry(tracer_provider=mock_provider)
      mock_set.assert_called_once_with(mock_provider)

  @unittest.skipUnless(HAS_OTEL_SDK, 'opentelemetry-sdk not installed')
  @mock.patch('dftimewolf.config.Config.GetExtra')
  @mock.patch(
      'opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter'
  )
  @mock.patch('opentelemetry.sdk.trace.TracerProvider')
  def testSetupOpenTelemetryOtlpHttp(self, mock_provider_cls, mock_exporter_cls, mock_get_extra):
    """Tests SetupOpenTelemetry with otlp-http mode."""
    mock_get_extra.return_value = {'type': 'google_cloud_spanner', 'config': {'opentelemetry': {'enabled': True, 'mode': 'otlp-http'}}}
    SetupOpenTelemetry()
    mock_exporter_cls.assert_called_once()
    mock_provider_cls.assert_called_once()

  def testSafeTelemetryCallDecoratorCatchesExceptions(self):
    """Tests that @safe_telemetry_call catches exceptions and returns None."""
    @safe_telemetry_call
    def failing_function():
      raise RuntimeError('Simulated telemetry failure')

    result = failing_function()
    self.assertIsNone(result)

  @mock.patch('dftimewolf.config.Config.GetExtra')
  def testGetCurrentSpan(self, mock_get_extra):
    """Tests get_current_span returns None when disabled, and active when enabled."""
    mock_get_extra.return_value = {'type': 'google_cloud_spanner', 'config': {'opentelemetry': {'enabled': False}}}
    self.assertIsNone(get_current_span())

    mock_get_extra.return_value = {'type': 'google_cloud_spanner', 'config': {'opentelemetry': {'enabled': True, 'mode': 'otlp-http'}}}
    span = get_current_span()
    self.assertIsNotNone(span)

  def testAddAttributeToCurrentSpan(self):
    """Tests adding attributes (serializable and non-serializable)."""
    # Primitive types
    add_attribute_to_current_span('test_key', 'test_val')
    add_attribute_to_current_span('test_int', 123)

    # Complex object (json serializable dict)
    add_attribute_to_current_span('test_dict', {'a': 1})

    # Non-serializable object (falls back to str(object))
    class CustomObj:
      def __str__(self):
        return 'CustomObjStr'
    add_attribute_to_current_span('test_custom', CustomObj())

  def testAddEventToCurrentSpan(self):
    """Tests adding events (annotations) with attributes to current span."""
    add_event_to_current_span('TestEvent', {'key': 'val'})
    add_event_to_current_span('TestEventNoAttrs')

  def testStartSpanContextManager(self):
    """Tests start_span context manager executes block safely."""
    block_executed = False
    with start_span('TestSpan', {'attr': 'val'}) as span:
      block_executed = True

    self.assertTrue(block_executed)

  def testStartSpanContextManagerExceptionHandling(self):
    """Tests start_span context manager handles exceptions in block."""
    block_executed = False
    try:
      with start_span('FailingSpan') as span:
        raise ValueError('Test Exception')
    except ValueError:
      block_executed = True

    self.assertTrue(block_executed)

  def testStartSpanContextManagerFailureTolerance(self):
    """Tests start_span executes inner block even if tracer fails."""
    with mock.patch('opentelemetry.trace.get_tracer') as mock_get_tracer:
      mock_tracer = mock.MagicMock()
      mock_tracer.start_as_current_span.side_effect = RuntimeError(
          'Tracer failed'
      )
      mock_get_tracer.return_value = mock_tracer

      block_executed = False
      with start_span('FailingSpan') as span:
        block_executed = True
        self.assertIsNone(span)

      self.assertTrue(block_executed)

  def testBaseModuleLogTelemetryWithAndWithoutTelemetry(self):
    """Tests BaseModule.LogTelemetry works when telemetry is or isn't set."""
    class DummyModule(module.BaseModule):
      def Process(self):
        pass
      def SetUp(self):
        pass

    container_mgr = mock.MagicMock()
    cache_obj = mock.MagicMock()
    callback = mock.MagicMock()

    # Case 1: Telemetry component is None
    mod_no_telemetry = DummyModule(
        name='TestModuleNoTelemetry',
        container_manager_=container_mgr,
        cache_=cache_obj,
        telemetry_=cast(Any, None),
        publish_message_callback=callback,
    )
    # Logging telemetry shouldn't crash when telemetry component is None
    mod_no_telemetry.LogTelemetry({'key1': 'val1'})
    mod_no_telemetry.LogTelemetryEvent('Event1', {'attr1': 'val1'})

    # Case 2: Telemetry component is present
    mock_telemetry_obj = mock.MagicMock()
    mod_with_telemetry = DummyModule(
        name='TestModuleWithTelemetry',
        container_manager_=container_mgr,
        cache_=cache_obj,
        telemetry_=mock_telemetry_obj,
        publish_message_callback=callback,
    )
    mod_with_telemetry.LogTelemetry({'key2': 'val2'})
    mock_telemetry_obj.LogTelemetry.assert_called_once_with(
        'key2', 'val2', 'DummyModule'
    )
    mod_with_telemetry.LogTelemetryEvent('Event2', {'attr2': 'val2'})


if __name__ == '__main__':
  unittest.main()
