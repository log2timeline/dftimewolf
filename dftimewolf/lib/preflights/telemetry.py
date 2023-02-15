"""Telemetry module."""
import datetime
from typing import Optional
import uuid

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState

from google.cloud import spanner

class Telemetry(module.PreflightModule):
  """Sends telemetry data to Google Cloud Spanner."""

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a Telemetry object."""
    super(Telemetry, self).__init__(state, name=name, critical=critical)
    self.database = None
    self.uuid = None

  # pylint: disable=arguments-differ
  def SetUp(self,
            project_name: str,
            instance_name: str,
            database_name: str) -> None:
    spanner_client = spanner.Client(project=project_name)
    instance = spanner_client.instance(instance_name)
    self.database = instance.database(database_name)

    # In another life, we'd get the WF ID from somewhere else,
    # but for now, we'll just generate a UUID.
    self.uuid = str(uuid.uuid4())
    self.LogWorkflowStart()
    self.logger.success(f'dfTimewolf Workflow UUID: {self.uuid}')

    # Setup streaming handlers
    self.state.RegisterStreamingCallback(
      self.LogTelemetryContainer,
      containers.Telemetry)

    telemetry_container = containers.Telemetry(
      'Workflow started',
      str(datetime.datetime.now()))
    self.StreamContainer(telemetry_container)


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
      for row in result:
        self.logger.info(f'\t{row[1]}:\t\t{row[2]} - {row[3]}: {row[4]}')

    self.logger.info(f'Getting all telemetry for Workflow {self.uuid}...')
    self.database.run_in_transaction(_GetAllWorkflowTelemetryTransaction)

  def LogWorkflowStart(self):
    """Logs the start of a Workflow."""
    def _LogWorkflowStartTransaction(transaction, params: dict):
      # Using keys() and values() is not deterministic enough.
      columns = []
      values = []
      for key, value in params.items():
        columns.append(key)
        values.append(value)
      transaction.insert(table='Workflow', columns=columns, values=[values])

    modules = [m['name'] for m in self.state.recipe.get('modules', [])]
    modules.extend([m['name'] for m in self.state.recipe.get('preflights', [])])
    params = {
      'uuid': self.uuid,
      'creation_time': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
      'recipe': self.state.recipe.get('name', 'Unknown Recipe'),
      'modules': ','.join(modules),
      'preflights_delta': '0',
      'setup_delta': '0',
      'run_delta': '0',
      'total_time': '0',
      'metadata': '',
    }
    self.database.run_in_transaction(_LogWorkflowStartTransaction, params)

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

  def LogTelemetryContainer(self, container: containers.Telemetry) -> None:
    """Logs a telemetry event."""
    self.LogTelemetry(container.key, container.value, container.src_module_name)


  def Process(self) -> None:
    # Unused, everything happens streaming.
    pass

  def CleanUp(self) -> None:
    self.GetAllWorkflowTelemetry()


modules_manager.ModulesManager.RegisterModule(Telemetry)
