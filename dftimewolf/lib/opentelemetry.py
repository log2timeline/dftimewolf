# -*- coding: utf-8 -*-
"""Sets up OpenTelemetry for dfTimewolf.

To enable tracing, set the DFTIMEWOLF_OTEL_MODE environment variable or
specify `telemetry.otel_mode` in ~/.dftimewolfrc:
      - 'otlp-http' (Recommended): Export traces via HTTP OTLP to an
        OpenTelemetry collector or Cloud Trace (endpoint:
        DFTIMEWOLF_OTLP_HTTP_ENDPOINT, default: http://localhost:4318/v1/traces).
      - 'otlp-grpc': Export traces via gRPC OTLP to an OpenTelemetry
        collector (endpoint: DFTIMEWOLF_OTLP_GRPC_ENDPOINT, default:
        localhost:4317).

If telemetry is disabled or unset, all telemetry helper functions return safely
without performance overhead or side effects.

Use `start_span` as a context manager for adding sub-span tracing to methods
we want to instrument (such as API calls, uploads, or discrete tasks).

Example usage in dfTimewolf modules:
    ```python
    # Log module telemetry attribute
    self.LogTelemetry({'sketch_id': '1234'})

    # Log point-in-time annotation event
    self.LogTelemetryEvent('UploadStarted', {'file_size': 1024})

    # Sub-span tracing for methods we want to instrument
    from dftimewolf.lib import opentelemetry

    with opentelemetry.start_span('Timesketch.Upload', {'sketch_id': '1234'}):
      ...
    ```
"""

import contextlib
import functools
import json
import logging
import os
from typing import Any, Callable, Iterator, ParamSpec, TypeVar

from opentelemetry import context as otel_context
from opentelemetry import trace

logger = logging.getLogger('dftimewolf')

ROOT_SPAN = None
P = ParamSpec('P')
T = TypeVar('T')


def safe_telemetry_call(func: Callable[P, T]) -> Callable[P, T | None]:
  """Decorator to ensure telemetry calls never crash the application.

  Observability is a best-effort, auxiliary concern. Under no circumstances
  should a failure in telemetry initialization, span modification, or context
  propagation terminate a critical forensic recipe or workflow.

  Args:
    func: The telemetry function to wrap.

  Returns:
    The wrapped function returning None if an exception occurs during execution.
  """
  @functools.wraps(func)
  def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
    try:
      return func(*args, **kwargs)
    except Exception as e:  # pylint: disable=broad-except
      logger.warning('Telemetry operation %s failed: %s', func.__name__, e)
      return None
  return wrapper


def is_enabled() -> bool:
  """Returns True if telemetry is enabled.

  Checks `telemetry.config.opentelemetry.enabled` configuration.

  Returns:
    bool: True if OpenTelemetry is enabled.
  """
  try:
    # pylint: disable=g-import-not-at-top
    # pytype: disable=import-error
    from dftimewolf import config
    telemetry_config = config.Config.GetExtra('telemetry')
    otel_config = telemetry_config.get('config', {}).get('opentelemetry', {})
    return bool(otel_config.get('enabled', False))
  except Exception:  # pylint: disable=broad-except
    return False


def _clean_attribute_value(value: Any) -> Any:
  """Ensures attribute value is primitive or JSON serializable for OpenTelemetry."""
  if isinstance(value, (str, float, int, bool, list, tuple)):
    return value
  try:
    return json.dumps(value)
  except (TypeError, ValueError):
    return str(value)


@safe_telemetry_call
def get_current_span() -> trace.Span | None:
  """Gets the current span, or creates a new root span if none exists."""
  if not is_enabled():
    return None
  span = trace.get_current_span()
  if span and span.is_recording():
    return span
  global ROOT_SPAN
  if ROOT_SPAN:
    return ROOT_SPAN
  tracer = trace.get_tracer('dftimewolf')
  ROOT_SPAN = tracer.start_span('dftimewolf')
  return ROOT_SPAN


@safe_telemetry_call
def get_context() -> otel_context.Context | None:
  """Gets the context from the current span."""
  if not is_enabled():
    return None
  span = get_current_span()
  if span and span.is_recording():
    return trace.set_span_in_context(span)
  return None


@safe_telemetry_call
def add_attribute_to_current_span(name: str, value: Any) -> None:
  """Adds an attribute to the current OpenTelemetry span.

  Args:
    name: the name for the attribute.
    value: the value of the attribute.
  """
  if not is_enabled():
    return
  span = get_current_span()
  if not span or not span.is_recording():
    return
  span.set_attribute(name, _clean_attribute_value(value))


@safe_telemetry_call
def add_event_to_current_span(
    event_name: str, attributes: dict[str, Any] | None = None
) -> None:
  """Adds an event (annotation) to the current OpenTelemetry span.

  Args:
    event_name: The name or description of the event.
    attributes: Optional dictionary of attributes to attach to the event.
  """
  if not is_enabled():
    return
  span = get_current_span()
  if not span or not span.is_recording():
    return

  event_attributes: dict[str, Any] = {}
  if attributes:
    for k, v in attributes.items():
      event_attributes[k] = _clean_attribute_value(v)

  span.add_event(
      event_name, attributes=event_attributes if event_attributes else None
  )


@contextlib.contextmanager
def start_span(
    name: str, attributes: dict[str, Any] | None = None
) -> Iterator[trace.Span | None]:
  """Starts a child OpenTelemetry span within the current context safely.

  Use this context manager to instrument methods (such as API calls, uploads,
  or discrete processing tasks) for tracing.

  Args:
    name: The name of the span (e.g., 'GRR.ScheduleFlow', 'Timesketch.Upload').
    attributes: Optional dictionary of attributes to attach upon start.

  Yields:
    The active Span instance, or None if tracing is disabled/fails.
  """
  if not is_enabled():
    yield None
    return

  tracer = trace.get_tracer('dftimewolf')
  try:
    with tracer.start_as_current_span(name) as span:
      if span and span.is_recording() and attributes:
        for k, v in attributes.items():
          span.set_attribute(k, _clean_attribute_value(v))
      yield span
  except Exception as e:
    # pylint: disable=broad-exception-caught
    logger.warning(
        'Telemetry sub-span %s encountered error or could not be created: %s',
        name,
        e,
    )
    yield None


@safe_telemetry_call
def SetupOpenTelemetry(tracer_provider: trace.TracerProvider | None = None) -> None:
  """Sets up OpenTelemetry.

  To export traces to Google Cloud Trace, the preferred approach is using
  'otlp-http' mode (`DFTIMEWOLF_OTEL_MODE=otlp-http`) pointing to
  `https://telemetry.googleapis.com/v1/traces`.

  Args:
    tracer_provider: The tracer provider to use. If None, checks environment.
  """
  if tracer_provider:
    trace.set_tracer_provider(tracer_provider)
    return

  if not is_enabled():
    return

  otel_mode = 'otlp-http'
  try:
    # pylint: disable=g-import-not-at-top
    # pytype: disable=import-error
    from dftimewolf import config
    telemetry_config = config.Config.GetExtra('telemetry')
    otel_config = telemetry_config.get('config', {}).get('opentelemetry', {})
    otel_mode = otel_config.get('mode', 'otlp-http').lower()
  except Exception:  # pylint: disable=broad-except
    pass

  try:
    # pylint: disable=g-import-not-at-top
    # pytype: disable=import-error
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
  except ImportError as e:
    logger.warning(
        'OpenTelemetry SDK not installed, cannot configure mode %s: %s',
        otel_mode,
        e,
    )
    return

  resource = Resource.create({'service.name': 'dftimewolf'})
  trace_exporter = None

  if otel_mode == 'otlp-grpc':
    try:
      # pylint: disable=g-import-not-at-top
      # pytype: disable=import-error
      from opentelemetry.exporter.otlp.proto.grpc import trace_exporter as grpc_exporter
      endpoint = os.environ.get('DFTIMEWOLF_OTLP_GRPC_ENDPOINT', 'localhost:4317')
      insecure = os.environ.get('DFTIMEWOLF_OTLP_INSECURE', 'true').lower() == 'true'
      trace_exporter = grpc_exporter.OTLPSpanExporter(
          endpoint=endpoint, insecure=insecure
      )
    except ImportError as e:
      logger.warning('gRPC OTLP exporter not installed: %s', e)
  elif otel_mode == 'otlp-http':
    try:
      # pylint: disable=g-import-not-at-top
      # pytype: disable=import-error
      from opentelemetry.exporter.otlp.proto.http import trace_exporter as http_exporter
      endpoint = os.environ.get(
          'DFTIMEWOLF_OTLP_HTTP_ENDPOINT', 'http://localhost:4318/v1/traces'
      )
      trace_exporter = http_exporter.OTLPSpanExporter(endpoint=endpoint)
    except ImportError as e:
      logger.warning('HTTP OTLP exporter not installed: %s', e)
  else:
    logger.warning('Unsupported DFTIMEWOLF_OTEL_MODE: %s', otel_mode)

  if trace_exporter:
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(provider)
    logger.info('OpenTelemetry initialized with mode: %s', otel_mode)
