# -*- coding: utf-8 -*-
"""Processes Google Cloud Platform (GCP) logs for loading into Timesketch."""

import tempfile
import json

from dftimewolf.lib.module import BaseModule
from dftimewolf.lib.containers import containers

from dftimewolf.lib.modules import manager as modules_manager


class GCPLoggingTimesketch(BaseModule):
  """Transforms Google Cloud Platform logs for Timesketch."""

  def SetUp(self, *args, **kwargs):
    """Sets up necessary module configuration options."""
    # No configuration required.

  def __init__(self, state):
    super(GCPLoggingTimesketch, self).__init__(state)

  def _ProcessLogLine(self, log_line, query, project_name):
    """Processes a single JSON formatted Google Clod Platform log line.

    Args:
      log_line (str): a JSON formatted GCP log entry.
      query (str): the GCP query used to retrieve the log.
      project_name (str): name of the GCP project associated with the query.

    Returns:
      str: a Timesketch-friendly version of the log line.
    """
    log_record = json.loads(log_line)

    # Metadata about how the record was obtained.
    timesketch_record = {'query': query, 'project_name': project_name}

    # Timestamp related fields.
    timestamp = log_record.get('timestamp', None)
    if timestamp:
      timesketch_record['datetime'] = timestamp
      timesketch_record['timestamp_desc'] = 'Event Recorded'

    # General resource information.
    resource = log_record.get('resource', None)
    if resource:
      labels = resource.get('labels', None)
      if labels:
        for attribute, value in labels.items():
          timesketch_attribute = 'resource_label_{0:s}'.format(attribute)
          timesketch_record[timesketch_attribute] = value

    # The log entry will have either a jsonPayload, a protoPayload or a
    # textPayload.
    json_payload = log_record.get('jsonPayload', None)
    if json_payload:
      self._ParseJSONPayload(json_payload, timesketch_record)

    proto_payload = log_record.get('protoPayload', None)
    if proto_payload:
      self._parse_proto_payload(proto_payload, timesketch_record)

    text_payload = log_record.get('textPayload', None)
    if text_payload:
      timesketch_record['textPayload'] = text_payload

    self._BuildMessageString(timesketch_record)

    return json.dumps(timesketch_record)

  def _parse_proto_payload(self, proto_payload, timesketch_record):
    """Extracts information from a protoPayload field in a GCP log.

    protoPayload is set for all cloud audit events.

    Args:
      proto_payload (dict): the contents of a GCP protoPayload field.
      timesketch_record (dict): a dictionary that will be serialized to JSON
        and uploaded to Timesketch.
    """
    authentication_info = proto_payload.get('authenticationInfo', None)
    if authentication_info:
      principal_email = authentication_info.get('principalEmail', None)
      if principal_email:
        timesketch_record['principalEmail'] = principal_email

    request_metadata = proto_payload.get('requestMetadata', None)
    if request_metadata:
      for attribute, value in request_metadata.items():
        timesketch_attribute = 'requestMetadata_{0:s}'.format(attribute)
        timesketch_record[timesketch_attribute] = value

    proto_attributes = ['serviceName', 'methodName', 'resourceName']
    for attribute in proto_attributes:
      value = proto_payload.get(attribute, None)
      if value:
        timesketch_record[attribute] = value

    request = proto_payload.get('request', None)
    if request:
      self._ParseProtoPayloadRequest(request, timesketch_record)

  def _ParseProtoPayloadRequest(self, request, timesketch_record):
    """Extracts information from the request field of a protoPayload field.

    Args:
      request (dict): the contents of a GCP request field from a
          protoPayload field.
      timesketch_record (dict): a dictionary that will be serialized to JSON
        and uploaded to Timesketch.
    """
    request_attributes = [
        'name', 'description', 'direction', 'member', 'targetTags', 'email',
        'account_id'
    ]
    for attribute in request_attributes:
      if attribute in request:
        timesketch_attribute = 'request_{0:s}'.format(attribute)
        timesketch_record[timesketch_attribute] = request[attribute]

    # Firewall specific attributes.
    if 'sourceRanges' in request:
      source_ranges = ', '.join(request['sourceRanges'])
      timesketch_record['source_ranges'] = source_ranges

    if 'alloweds' in request:
      for allowed in request['alloweds']:
        attribute_name = 'allowed_{0:s}_ports'.format(allowed['IPProtocol'])
        if 'ports' in allowed:
          timesketch_record[attribute_name] = allowed['ports']
        else:
          timesketch_record[attribute_name] = 'all'

    if 'denieds' in request:
      for denied in request['denieds']:
        attribute_name = 'denied_{0:s}_ports'.format(denied['IPProtocol'])
        if 'ports' in denied:
          timesketch_record[attribute_name] = denied['ports']
        else:
          timesketch_record[attribute_name] = 'all'

    # Service account specific attributes
    if 'service_account' in request:
      service_account_name = request['service_account'].get('display_name')
      timesketch_record['service_account_display_name'] = service_account_name

  def _ParseJSONPayload(self, json_payload, timesketch_record):
    """Extracts information from a json_payload.

    Args:
      json_payload (dict): the contents of a GCP jsonPayload field.
      timesketch_record (dict): a dictionary that will be serialized to JSON
        and uploaded to Timesketch.
    """
    json_attributes = ['event_type', 'event_subtype']
    for attribute in json_attributes:
      if attribute in json_payload:
        timesketch_record[attribute] = json_payload[attribute]

    actor = json_payload.get('actor', None)
    if actor:
      if 'user' in actor:
        timesketch_record['user'] = actor['user']

  def _BuildMessageString(self, timesketch_record):
    """Builds a Timesketch message string from a Timesketch record.

    Args:
      timesketch_record (dict): a dictionary that will be serialized to JSON
        and uploaded to Timesketch.
    """
    user = ''
    action = ''
    resource = ''

    # Ordered from least to most preferred value
    user_attributes = ['principalEmail', 'user']
    for attribute in user_attributes:
      if attribute in timesketch_record:
        user = timesketch_record[attribute]

    # Ordered from least to most preferred value
    action_attributes = ['methodName', 'event_subtype']
    for attribute in action_attributes:
      if attribute in timesketch_record:
        action = timesketch_record[attribute]

    # Ordered from least to most preferred value
    resource_attributes = ['resource_label_instance_id', 'resourceName']
    for attribute in resource_attributes:
      if attribute in timesketch_record:
        resource = timesketch_record[attribute]

    # Textpayload records can be anything, so we don't want to try to format
    # them.
    if timesketch_record.get('textPayload', False):
      message = timesketch_record['textPayload']
    else:
      message = 'User {0:s} performed {1:s} on {2:s}'.format(
          user, action, resource)

    timesketch_record['message'] = message

  def _ProcessLogContainer(self, logs_container):
    """Processes a GCP logs container.

    Args:
      logs_container (GCPLogs): logs container.
    """
    if not logs_container.path:
      return

    output_file = tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', delete=False, suffix='.jsonl')
    output_path = output_file.name

    with open(logs_container.path, 'r') as input_file:
      for line in input_file:
        transformed_line = self._ProcessLogLine(
            line, logs_container.filter_expression, logs_container.project_name)
        if transformed_line:
          output_file.write(transformed_line)
          output_file.write('\n')
    output_file.close()

    timeline_name = 'GCP logs {0:s} "{1:s}"'.format(
        logs_container.project_name, logs_container.filter_expression)

    self.state.output.append([timeline_name, output_path])

  def Process(self):
    """Processes GCP logs containers for insertion into Timesketch."""
    logs_containers = self.state.GetContainers(containers.GCPLogs)
    for logs_container in logs_containers:
      self._ProcessLogContainer(logs_container)

modules_manager.ModulesManager.RegisterModule(GCPLoggingTimesketch)
