"""Telemetry module."""
import datetime
import uuid

from google.cloud import spanner

class Telemetry():
  """Sends telemetry data to Google Cloud Spanner."""

  # Make telemetry a singleton.
  def __new__(cls, *args, **kwargs):
    if not hasattr(cls, 'instance'):
      cls.instance = super(Telemetry, cls).__new__(cls)
    return cls.instance

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


  def GetAllWorkflowTelemetry(self):
    """Gets all telemetry for a given workflow UUID."""
    def _GetAllWorkflowTelemetryTransaction(transaction):
      query = (
        'SELECT * from Telemetry WHERE workflow_uuid = @uuid ORDER BY time ASC'
      )
      result = transaction.execute_sql(
        query,
        params={'uuid': self.uuid},
        param_types={'uuid': spanner.param_types.STRING})
      # for row in result:
      #   self.logger.info(f'\t{row[1]}:\t\t{row[2]} - {row[3]}: {row[4]}')

    # self.logger.info(f'Getting all telemetry for Workflow {self.uuid}...')
    self.database.run_in_transaction(_GetAllWorkflowTelemetryTransaction)

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

  def UpdateWorkflowtelemetry(self, key: str, value: int) -> None:
    def _UpdateWorkflowtelemetryTransaction(transaction, key: str, value: str):
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
      _UpdateWorkflowtelemetryTransaction, key, value)

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

  def LogTelemetryContainer(
    self, key: str, value: str, src_module_name: str) -> None:
    """Logs a telemetry event."""
    self.LogTelemetry(key, value, src_module_name)
