# -*- coding: utf-8 -*-
"""Processes Google Workspace logs for loading into Timesketch."""

import os
import tempfile
import json
import string

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from dftimewolf.lib.module import BaseModule
from dftimewolf.lib.containers import containers

from dftimewolf.lib.modules import manager as modules_manager

if TYPE_CHECKING:
  from dftimewolf.lib import state

class WorkspaceAuditTimesketch(BaseModule):
  """Transforms Google Workspace logs for Timesketch."""

  _FORMAT_STRINGS_PATH = os.path.join(os.path.dirname(__file__),
      'workspace_format_strings.json')

  _IGNORABLE_RECORD_FIELDS = [
      'time', 'datetime', 'timestamp', 'data_type', 'timestamp_desc'
  ]

  def __init__(self,
               state: "state.DFTimewolfState",
               name: Optional[str]=None,
               critical: bool=False):
    super(WorkspaceAuditTimesketch, self).__init__(
        state, name=name, critical=critical)

    with open(self._FORMAT_STRINGS_PATH, 'r') as formatters_json:
      self._all_application_format_strings = json.load(formatters_json)

  def SetUp(self, *args, **kwargs): # type: ignore
    """Sets up necessary module configuration options."""
    # No configuration required.

  def _ExtractActorInformation(
      self, actor_dict: Dict[str, str]) -> Dict[str, Optional[str]]:
    """Extracts actor information from a Workspace log record.

    Args:
      actor_dict (dict): contents of the 'actor' dict in a Workspace log record

    Returns:
      dict[str, str]: a dictionary containing actor information suitable for
          adding to a Timesketch record.
    """
    return {
        'actor_email': actor_dict.get('email'),
        'actor_profileId': actor_dict.get('profileId'),
        'actor_callerType': actor_dict.get('callerType'),
        'actor_key': actor_dict.get('key')}

  def _FlattenParameters(
      self, parameters: List[Dict[str, str]]) -> Dict[str, str]:
    """Flattens out parameter information from a Workspace log record.

    The parameter list looks like this:
      [{"name": "event_id", "value": "4"}, {"name": "title", "value": "foo"}]

    This method turns it into:
      {"event_id": "4", "title": "foo"}

    Args:
      parameters (list): the contents of a Workspace parameters list.

    Returns:
      dict[str, str]: a dictionary containing parameter information suitable for
          adding to a Timesketch record.
    """
    parameters_dict = {}
    for parameter in parameters:
      name = parameter.get('name')
      if not name:
        self.ModuleError(
            'Encountered a parameter with no name. '
            'Full parameter dictionary: {0:s}'.format(str(parameters)))
        continue
      name = name.lower()
      value = parameter.get('value')  # type: Optional[str]
      if not value:
        multivalue = parameter.get('multiValue', '')  # type: str
        value = ', '.join(multivalue)
      if name and value:
        parameters_dict[name] = str(value)
    return parameters_dict

  def _AddMessageString(self, timesketch_record: Dict[str, Any]) -> None:
    """Builds a Timesketch message string from a Timesketch record.

    Args:
      timesketch_record (dict): a dictionary that will be serialized to JSON
        and uploaded to Timesketch.
    """
    application_name = timesketch_record.get('applicationName')
    format_strings = self._all_application_format_strings.get(
        application_name, {})
    if not format_strings:
      self.logger.warning(
          'No format strings found for application name {0:s}'.format(
              application_name))
    event_name = timesketch_record.get('_event_name', '').lower()
    format_string = format_strings.get(event_name)

    if not format_string:
      self.logger.warning(
          'No format strings found for event_name {0:s}'.format(event_name))
      columns = [
          f'{{{field}}}' for field in timesketch_record.keys()
          if field not in self._IGNORABLE_RECORD_FIELDS
      ]
      format_string = ' '.join(columns)

    message = ''
    formatter = string.Formatter()
    for literal_text, field, _, _ in formatter.parse(format_string):
      message = message + literal_text
      if field:
        if field == 'actor':
          actor = (timesketch_record.get('actor_email') or
                   timesketch_record.get('actor_profileId') or
                   timesketch_record.get('actor_key'))
          message += '{0:s}'.format(actor)
          continue
        value = timesketch_record.get(field)
        if not value:
          value = timesketch_record.get(field.lower())
        if not value:
          value = ''
        message += '{0:s}'.format(value)

    timesketch_record['message'] = message

  def _ProcessLogLine(self, log_record_string: str) -> List[str]:
    """Processes a single JSON formatted Google Workspace log line.

    Args:
      log_record_string (str): a JSON formatted Workspace log entry.

    Returns:
      list[str]: one or more Timesketch records.
    """
    log_record = json.loads(log_record_string)
    actor = self._ExtractActorInformation(log_record.pop('actor', {}))
    identifiers = log_record.pop('id', {})
    timestamp = identifiers.pop('time')
    events = log_record.pop('events', [])
    timesketch_records = []
    for event in events:
      timesketch_record = {
          'datetime': timestamp,
          'timestamp_desc': 'Event Recorded',
          '_event_type': event.get('type'),
          '_event_name': event.get('name'),
      }
      timesketch_record.update(actor)
      timesketch_record.update(identifiers)
      timesketch_record.update(log_record)

      parameters = self._FlattenParameters(event.get('parameters', {}))
      timesketch_record.update(parameters)

      self._AddMessageString(timesketch_record)

      timesketch_records.append(json.dumps(timesketch_record))
    return timesketch_records

  def _ProcessLogContainer(
      self, logs_container: containers.WorkspaceLogs) -> None:
    """Processes a Workspace logs container.

    Args:
      logs_container (WorkspaceLogs): logs container.
    """
    if not logs_container.path:
      self.ModuleError('Encountered a logs container with an empty path')
      return

    output_file = tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', delete=False, suffix='.jsonl')
    output_path = output_file.name
    self.logger.info(
        'Adding Timesketch attributes to logs from {0:s} to {1:s}'.format(
            logs_container.path, output_path))

    with open(logs_container.path, 'r') as input_file:
      for line in input_file:
        transformed_lines = self._ProcessLogLine(line)
        for transformed_line in transformed_lines:
          output_file.write(transformed_line)
          output_file.write('\n')
    output_file.close()

    timeline_name = 'Workspace {0:s} logs'.format(
        logs_container.application_name)
    if logs_container.user_key:
      timeline_name = f'{timeline_name} for {logs_container.user_key}'
    if logs_container.start_time:
      timeline_name = f'{timeline_name} from {logs_container.start_time}'
    if logs_container.end_time:
      timeline_name = f'{timeline_name} to {logs_container.end_time}'
    if logs_container.filter_expression:
      timeline_name = (
          f'{timeline_name} filter {logs_container.filter_expression}')

    container = containers.File(name=timeline_name, path=output_path)
    self.state.StoreContainer(container)

  def Process(self) -> None:
    """Processes Workspace logs containers for insertion into Timesketch."""
    logs_containers = self.state.GetContainers(containers.WorkspaceLogs)
    for logs_container in logs_containers:
      self._ProcessLogContainer(logs_container)


modules_manager.ModulesManager.RegisterModule(WorkspaceAuditTimesketch)
