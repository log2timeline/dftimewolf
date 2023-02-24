"""Telemetry module."""
import datetime
from dataclasses import dataclass
from typing import Dict, Any, List, Union
import uuid

from google.cloud import spanner  # type: ignore

from dftimewolf import config


@dataclass
class TelemetryEntry:
  """A simple dataclass to store module-related statistics.

  Attributes:
    module_type: Type of the module that generated the telemetry.
    module_name: Name of the module that generated the telemetry. This has the
        same value as module_type when no runtime_name has been specified for
        the module.
    telemetry: Dictionary of telemetry to store. Contents are arbitrary, but
        keys must be strings.
  """
  module_type: str
  module_name: str
  telemetry: Dict[str, str]

class BaseTelemetry():
  """Interface for implementing a telemetry module."""

  def __new__(cls, *args: Any, **kwargs: Dict[str, Any]) -> "BaseTelemetry": # pylint: disable=unused-argument
    if not hasattr(cls, 'instance'):
      cls.instance = super(BaseTelemetry, cls).__new__(cls)
    return cls.instance

  def __init__(self) -> None:
    """Initializes a BaseTelemetry object."""
    super().__init__()
    self.uuid = str(uuid.uuid4())
    self.entries = [] # type: List[str]

  def FormatTelemetry(self) -> str:
    """Gets all telemetry for a given workflow UUID."""
    output = [f'Telemetry information for: {self.uuid}']
    output.extend(self.entries)
    return '\n'.join(output)

  def LogTelemetry(self, key: str, value: str, src_module_name: str) -> None:
    """Logs a telemetry event.

    Args:
      key: Telemetry key.
      value: Telemetry value.
      src_module_name: Name of the module that generated the telemetry.
    """
    entry = f'\t{key}: \t{value} ({src_module_name})'
    self.entries.append(entry)


class GoogleCloudSpannerTelemetry(BaseTelemetry):
  """Sends telemetry data to Google Cloud Spanner."""

  def __init__(self, **kwargs: Dict[str, Any]) -> None:
    """Initializes a GoogleCloudSpannerTelemetry object."""
    if hasattr(self, 'database'):  # Already initialized
      return
    super().__init__()
    spanner_client = spanner.Client(project=kwargs['project_name'])
    instance = spanner_client.instance(kwargs['instance_name'])
    self.database = instance.database(kwargs['database_name'])

  def FormatTelemetry(self) -> str:
    """Gets all telemetry for a given workflow UUID."""
    entries = []  # type: List[str]
    self.database.run_in_transaction(
      self._GetAllWorkflowTelemetryTransaction, entries=entries)
    return '\n'.join(entries)

  def _GetAllWorkflowTelemetryTransaction(self, transaction: Any, entries: List[str]) -> None:
    entries.append(f'Telemetry information for: {self.uuid}')
    query = (
      'SELECT * from Telemetry WHERE workflow_uuid = @uuid ORDER BY time ASC'
    )
    result = transaction.execute_sql(
      query,
      params={'uuid': self.uuid},
      param_types={'uuid': spanner.param_types.STRING})
    for row in result:
      entries.append(f'\t{row[1]}:\t\t{row[2]} - {row[3]}: {row[4]}')

  def LogTelemetry(self, key: str, value: str, src_module_name: str) -> None:
    """Logs a telemetry event.

    Args:
      key: Telemetry key.
      value: Telemetry value.
      src_module_name: Name of the module that generated the telemetry.
    """

    telemetry = {
      'workflow_uuid': self.uuid,
      'time': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
      'source_module': src_module_name,
      'key': key,
      'value': value,
    }
    self.database.run_in_transaction(self._LogTelemetryTransaction, telemetry)

  def _LogTelemetryTransaction(self, transaction: Any, telemetry: Dict[str, str]) -> None:
    # Using items() provides a stable order for the columns and values
    columns = []
    values = []
    for key, value in telemetry.items():
      columns.append(key)
      values.append(value)
    transaction.insert(table='Telemetry', columns=columns, values=[values])

TELEMETRY = None  # type: Union[BaseTelemetry, GoogleCloudSpannerTelemetry, None]

def GetTelemetry() -> Union[BaseTelemetry, GoogleCloudSpannerTelemetry]:
  """Returns the currently configured Telemetry object."""
  # pylint: disable=global-statement
  global TELEMETRY
  if TELEMETRY is None:
    telemetry_config = config.Config.GetExtra('telemetry')
    if telemetry_config.get('type') == 'google_cloud_spanner':
      TELEMETRY = GoogleCloudSpannerTelemetry(**telemetry_config['config'])
    else:
      TELEMETRY = BaseTelemetry()
  return TELEMETRY

def LogTelemetry(key: str, value: str, src_module_name: str) -> None:
  """"Logs a Telemetry entry using the currently configured Telemetry object."""
  telemetry = GetTelemetry()
  telemetry.LogTelemetry(key, value, src_module_name)

def FormatTelemetry() -> str:
  """Formats the telemetry of the currently configured Telemetry object."""
  telemetry = GetTelemetry()
  return telemetry.FormatTelemetry()
