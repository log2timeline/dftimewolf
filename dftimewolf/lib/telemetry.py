"""Telemetry module."""
import datetime
from dataclasses import dataclass
import uuid

from google.cloud import spanner

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
  telemetry: dict[str, str]




class BaseTelemetry():
  """Interface for implementing a telemetry module."""
  def __init__(self) -> None:
    self.uuid = str(uuid.uuid4())
    self.entries = []
    self.workflow = {}

  def FormatTelemetry(self):
    """Gets all telemetry for a given workflow UUID."""
    output = [f'Telemetry information for: {self.uuid}']

    for key, value in self.workflow.items():
      output.append(f'\t{key}:\t\t{value}')
    output.extend(self.entries)
    return '\n'.join(output)

  def LogWorkflowStart(self, recipe_name: str, modules: set[str]) -> None:
    """Logs the start of a Workflow."""
    entry = f'Workflow started: recipe: {recipe_name}, modules: ({",".join(modules)})'
    self.entries.append(entry)
    print(entry)

  def UpdateWorkflowTelemetry(self, key: str, value: int) -> None:
    """Updates a workflow telemetry value."""
    self.workflow[key] = value

  def LogTelemetry(self, key: str, value: str, src_module_name: str) -> None:
    """Logs a telemetry event.

    Args:
      key: Telemetry key.
      value: Telemetry value.
      src_module_name: Name of the module that generated the telemetry.
    """
    entry = f'\tTelemetry added: \t{key}: \t{value} ({src_module_name})'
    self.entries.append(entry)
    print(entry)


class GoogleCloudSpannerTelemetry(BaseTelemetry):
  """Sends telemetry data to Google Cloud Spanner."""

  def __init__(self,
               project_name: str,
               instance_name: str,
               database_name: str) -> None:
    """Initializes a Telemetry object."""
    spanner_client = spanner.Client(project=project_name)
    instance = spanner_client.instance(instance_name)
    self.database = instance.database(database_name)

    # In another life, we'd get the WF ID from somewhere else,
    # but for now, we'll just generate a UUID.
    self.uuid = str(uuid.uuid4())

  def FormatTelemetry(self) -> str:
    """Gets all telemetry for a given workflow UUID."""
    entries = []
    def _GetAllWorkflowTelemetryTransaction(transaction, entries):
      entries.append(f'Telemetry information for: {self.uuid}')
      query = (
        'SELECT * from Workflow WHERE uuid = @uuid'
      )
      result = transaction.execute_sql(
        query,
        params={'uuid': self.uuid},
        param_types={'uuid': spanner.param_types.STRING})
      for row in result:
        entries.append(f'Workflow started on {row[1]}: recipe: {row[2]} (Modules: {row[3]})')
        entries.append(f'\tTotal time: {row[7]}')
        entries.append(f'\tPreflight time: {row[4]}')
        entries.append(f'\tSetup time: {row[5]}')
        entries.append(f'\tRun time: {row[6]}')

      query = (
        'SELECT * from Telemetry WHERE workflow_uuid = @uuid ORDER BY time ASC'
      )
      result = transaction.execute_sql(
        query,
        params={'uuid': self.uuid},
        param_types={'uuid': spanner.param_types.STRING})
      for row in result:
        entries.append(f'\t{row[1]}:\t\t{row[2]} - {row[3]}: {row[4]}')

    self.database.run_in_transaction(
      _GetAllWorkflowTelemetryTransaction, entries=entries)
    return '\n'.join(entries)

  def LogWorkflowStart(self, recipe_name: str, modules: set[str]) -> None:
    """Logs the start of a Workflow."""
    def _LogWorkflowStartTransaction(transaction, params: dict):
      # Using keys() and values() is not deterministic enough.
      columns = []
      values = []
      for key, value in params.items():
        columns.append(key)
        values.append(value)
      transaction.insert(table='Workflow', columns=columns, values=[values])

    params = {
      'uuid': self.uuid,
      'creation_time': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
      'recipe': recipe_name,
      'modules': ','.join(modules),
      'preflights_delta': '0',
      'setup_delta': '0',
      'run_delta': '0',
      'total_time': '0',
      'metadata': '',
    }
    self.database.run_in_transaction(_LogWorkflowStartTransaction, params)

  def UpdateWorkflowTelemetry(self, key: str, value: int) -> None:
    def _UpdateWorkflowTelemetryTransaction(transaction, key: str, value: str):
      transaction.execute_update(
        f'UPDATE Workflow SET {key} = @value WHERE uuid = @uuid',
        params={'key': key, 'value': value, 'uuid':self.uuid},
        param_types={
          # 'key': spanner.param_types.STRING,
          'value': spanner.param_types.INT64,
          'uuid': spanner.param_types.STRING
          })
    if key not in {
      'preflights_delta',
      'setup_delta',
      'run_delta',
      'total_time'}:
      raise ValueError(f'Invalid key {key}')
    self.database.run_in_transaction(
      _UpdateWorkflowTelemetryTransaction, key, value)

  def LogTelemetry(self, key: str, value: str, src_module_name: str) -> None:
    """Logs a telemetry event.

    Args:
      key: Telemetry key.
      value: Telemetry value.
      src_module_name: Name of the module that generated the telemetry.
    """
    def _LogTelemetryTransaction(transaction, telemetry: dict) -> None:
      # Using keys() and values() is not deterministic enough.
      columns = []
      values = []
      for key, value in telemetry.items():
        columns.append(key)
        values.append(value)
      transaction.insert(table='Telemetry', columns=columns, values=[values])

    telemetry = {
      'workflow_uuid': self.uuid,
      'time': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
      'source_module': src_module_name,
      'key': key,
      'value': value,
    }
    self.database.run_in_transaction(_LogTelemetryTransaction, telemetry)
