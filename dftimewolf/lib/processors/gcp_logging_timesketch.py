# -*- coding: utf-8 -*-
"""Processes Google Cloud Platform (GCP) logs for loading into Timesketch.

The following attributes are extracted by the processor:
  data_type: Timesketch data type i.e. gcp:log:json.
  datetime: event date time.
  dcsa_emails: default compute service account, a service account attached when
      a Compute Engine instance is created.
  dcsa_scopes: OAuth scopes granted to the default service account attached to a
      Compute Engine instance.
  delegation_chain: service account impersonation/delegation chain.
  event_subtype: event subtype.
  gcloud_command_id: unique gcloud command execution ID.
  gcloud_command_partial: partial gcloud command related to the operation.
  message: summary message of the operation.
  method_name: operation performed.
  permissions: IAM permissions used for the operation.
  policy_delta: IAM policy delta.
  principal_email: email address of the requester.
  principal_subject: subject of the requester.
  query: Google Cloud log filtering query.
  resource_label_instance_id: Compute Engine instance ID.
  resource_name: resource name.
  service_account_delegation: service accounts delegation in
      authentication.
  service_account_display_name: display name of the service account.
  service_account_key_name: service account key name used in
      authentication.
  service_name: name of the service.
  severity: log entry severity.
  source_images: source images of disks attached to a Compute Engine instance.
  source_ranges: firewall source ranges.
  status_code: operation success or failure code.
  status_message: operation success or failure message.
  status_reason: operation failure reasons.
  textPayload: text payload for logs not using a JSON or proto payload.
  timestamp_desc: description of timestamp.
  user: user or requester.
"""

import json
import re
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING

from dftimewolf.lib.containers import containers
from dftimewolf.lib.module import BaseModule
from dftimewolf.lib.modules import manager as modules_manager

if TYPE_CHECKING:
  from dftimewolf.lib import state


class GCPLoggingTimesketch(BaseModule):
  """Transforms Google Cloud Platform logs for Timesketch."""

  DATA_TYPE = 'gcp:log:json'

  def __init__(self,
               state: "state.DFTimewolfState",
               name: Optional[str]=None,
               critical: bool=False) -> None:
    super(GCPLoggingTimesketch, self).__init__(
        state, name=name, critical=critical)

  def SetUp(self, *args, **kwargs):  # type: ignore
    """Sets up necessary module configuration options."""
    # No configuration required.

  def _ProcessLogLine(self, log_line: str, query: str) -> str:
    """Processes a single JSON formatted Google Cloud Platform log line.

    Args:
      log_line (str): a JSON formatted GCP log entry.
      query (str): the GCP query used to retrieve the log.

    Returns:
      str: a Timesketch-friendly version of the log line.
    """
    log_record = json.loads(log_line)

    # Metadata about how the record was obtained.
    timesketch_record = {'query': query,
                         'data_type': self.DATA_TYPE}

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
          timesketch_attribute = attribute
          timesketch_record[timesketch_attribute] = value

    # Some Cloud logs pass through Severity from the underlying log source
    severity = log_record.get('severity', None)
    if severity:
      timesketch_record['severity'] = severity

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

  def _ParseAuthenticationInfo(
      self,
      proto_payload: Dict[str, Any],
      timesketch_record: Dict[str, Any]) -> None:
    """Extracts `protoPayload.authenticationInfo` field in a GCP log.

    Args:
      proto_payload: the content of a GCP protoPaylaod field.
      timesketch_record: a dictionary that will be serialized to JSON and
          uploaded to Timesketch.
    """
    authentication_info = proto_payload.get('authenticationInfo', None)
    if authentication_info:
      principal_email = authentication_info.get('principalEmail', None)
      if principal_email:
        timesketch_record['principal_email'] = principal_email

      principal_subject = authentication_info.get('principalSubject', None)
      if principal_subject:
        timesketch_record['principal_subject'] = principal_subject

      service_account_key_name = authentication_info.get(
          'serviceAccountKeyName', None)
      if service_account_key_name:
        timesketch_record['service_account_key_name'] = service_account_key_name

      # Service account delegation information
      delegations = []

      delegation_info_list = authentication_info.get(
          'serviceAccountDelegationInfo', [])
      for delegation_info in delegation_info_list:
        first_party_principal = delegation_info.get('firstPartyPrincipal', {})

        first_party_principal_email = first_party_principal.get(
            'principalEmail', None)
        if first_party_principal_email:
          delegations.append(first_party_principal_email)
        else:
          first_party_principal_subject = first_party_principal.get(
              'principalSubject', None)
          if first_party_principal_subject:
            delegations.append(first_party_principal_subject)

      if delegations:
        timesketch_record['service_account_delegation'] = delegations
        timesketch_record['delegation_chain'] = '->'.join(delegations)

  def _ParseAuthorizationInfo(
      self,
      proto_payload: Dict[str, Any],
      timesketch_record: Dict[str, Any]) -> None:
    """Extracts `protoPayload.authorizationInfo` field in a GCP log.

    Args:
      proto_payload: the content of a GCP protoPaylaod field.
      timesketch_record: a dictionary that will be serialized to JSON and
          uploaded to Timesketch.
    """
    permissions = []

    authorization_info_list = proto_payload.get('authorizationInfo', [])
    for authorization_info in authorization_info_list:
      permission = authorization_info.get('permission', None)
      if permission:
        permissions.append(permission)

    if permissions:
      timesketch_record['permissions'] = permissions

  def _ParseRequestMetadata(
      self,
      proto_payload: Dict[str, Any],
      timesketch_record: Dict[str, str]) -> None:
    """Extracts `protoPayload.requestMetadata` field in a GCP log.

    Args:
      proto_payload: the content of a GCP protoPaylaod field.
      timesketch_record: a dictionary that will be serialized to JSON and
          uploaded to Timesketch.
    """
    request_metadata = proto_payload.get('requestMetadata', {})

    # `protoPayload.callerIp` can be empty for some requests.
    caller_ip = request_metadata.get('callerIp', '')
    timesketch_record['caller_ip'] = caller_ip

    # `protoPayload.callerSuppliedUserAgent` can be empty for some requests.
    user_agent = request_metadata.get('callerSuppliedUserAgent', '')
    timesketch_record['user_agent'] = user_agent

    # Check for gcloud command invocation
    if user_agent:
      if 'command/' in user_agent:
        command_regex = re.search(r'command/([^\s]+)', user_agent)
        if command_regex:
          command_string = str(command_regex.group(1))
          command_string = command_string.replace('.', ' ')

          timesketch_record['gcloud_command_partial'] = command_string

      if 'invocation-id/' in user_agent:
        invocation_regex = re.search(r'invocation-id/([^\s]+)', user_agent)
        if invocation_regex:
          invocation_id = str(invocation_regex.group(1))
          timesketch_record['gcloud_command_id'] = invocation_id

  def _ParseProtoPayloadStatus(
      self,
      proto_payload: Dict[str, Any],
      timesketch_record: Dict[str, str]) -> None:
    """Extracts `protoPayload.status` field in a GCP log.

    Args:
      proto_payload: the content of a GCP protoPaylaod field.
      timesketch_record: a dictionary that will be serialized to JSON and
          uploaded to Timesketch.
    """
    status = proto_payload.get('status', {})

    # `protoPayload.status` can be an empty object which indicates successful
    # operation.
    #
    # Empty `status_code` and `status_message` are added to reflect the same.
    if not status:
      timesketch_record['status_code'] = ''
      timesketch_record['status_message'] = ''

      return

    # A non-empty `protoPayload.status` field could have empty
    # `protoPayload.status.code` and `protoPayload.status.message` fields.
    # Empty `code` and `message` fields would indicate the operation was
    # successful.
    status_code = str(status.get('code', ''))
    status_message = status.get('message', '')

    timesketch_record['status_code'] = status_code
    timesketch_record['status_message'] = status_message

    # `protoPayload.status` struction may contain `details` attribute when
    # operation fails. The reason attribute contains the reason the operation
    # failed.
    status_reasons = []

    status_details = status.get('details', [])
    for status_detail in status_details:
      reason = status_detail.get('reason')
      if reason:
        status_reasons.append(reason)

    if status_reasons:
      timesketch_record['status_reason'] = ', '.join(status_reasons)

  def _ParseServiceData(
      self,
      proto_payload: Dict[str, Any],
      timesketch_record: Dict[str, Any]) -> None:
    """Extracts information from `protoPayload.serviceData` field in a GCP log.

    Args:
      proto_payload: the content of a GCP protoPayload field.
      timesketch_record: a dictionary that will be serialized to JSON and
          uploaded to Timesketch.
    """
    service_data = proto_payload.get('serviceData', None)
    if service_data:
      policy_delta = service_data.get('policyDelta', None)
      if policy_delta:
        binding_deltas = policy_delta.get('bindingDeltas', [])
        if binding_deltas:
          policy_deltas = []
          for bd in binding_deltas:
            policy_deltas.append(
                '{0:s} {1:s} with role {2:s}'.format(
                    bd.get('action', ''), bd.get('member', ''),
                    bd.get('role', '')))
          timesketch_record['policy_delta'] = ', '.join(policy_deltas)

  def _parse_proto_payload(
      self,
      proto_payload: Dict[str, Any],
      timesketch_record: Dict[str, Any]) -> None:
    """Extracts information from a protoPayload field in a GCP log.

    protoPayload is set for all cloud audit events.

    Args:
      proto_payload (dict): the contents of a GCP protoPayload field.
      timesketch_record (dict): a dictionary that will be serialized to JSON
        and uploaded to Timesketch.
    """
    service_name = proto_payload.get('serviceName', '')
    if service_name:
      timesketch_record['service_name'] = service_name

    method_name = proto_payload.get('methodName', '')
    if service_name:
      timesketch_record['method_name'] = method_name

    resource_name = proto_payload.get('resourceName', '')
    if resource_name:
      timesketch_record['resource_name'] = resource_name

    self._ParseAuthenticationInfo(proto_payload, timesketch_record)
    self._ParseAuthorizationInfo(proto_payload, timesketch_record)
    self._ParseRequestMetadata(proto_payload, timesketch_record)
    self._ParseProtoPayloadRequest(proto_payload, timesketch_record)
    self._ParseProtoPayloadStatus(proto_payload, timesketch_record)
    self._ParseServiceData(proto_payload, timesketch_record)

  def _ParseComputeInstancesInsert(
      self,
      request: Dict[str, Any],
      timesketch_record: Dict[str, Any]) -> None:
    """ Extracts information related to compute instances insert.

    Args:
      request: the `protoPayload.request` field in a GCP log.
      timesketch_record: a dictionary that will be serialized to JSON and
          uploaded to Timesketch.
    """
    if not request:
      return

    request_type = request.get('@type', None)
    if not request_type:
      return

    if request_type != 'type.googleapis.com/compute.instances.insert':
      return

    # Source images are useful during investigaions.
    source_images = []

    disks = request.get('disks', [])
    for disk in disks:
      initialize_params = disk.get('initializeParams', {})

      source_image = initialize_params.get('sourceImage', None)
      if source_image:
        source_images.append(source_image)

    if source_images:
      timesketch_record['source_images'] = source_images

    # Default Compute Engine Service Account (dcsa)
    dcsa_emails = []
    dcsa_scopes = []

    service_accounts = request.get('serviceAccounts', [])
    for service_account in service_accounts:
      email = service_account.get('email', None)
      if email:
        dcsa_emails.append(email)

      scopes = service_account.get('scopes', [])
      if scopes:
        dcsa_scopes.extend(scopes)

    if dcsa_emails:
      timesketch_record['dcsa_emails'] = dcsa_emails

    if dcsa_scopes:
      timesketch_record['dcsa_scopes'] = dcsa_scopes

  def _ParseProtoPayloadRequest(
      self,
      proto_payload: Dict[str, Any],
      timesketch_record: Dict[str, Any]) -> None:
    """Extracts information from the `protoPayload.request` field of a GCP log.

    Args:
      proto_payload: the contents of a GCP protoPayload field from a
          protoPayload field.
      timesketch_record: a dictionary that will be serialized to JSON
        and uploaded to Timesketch.
    """
    request = proto_payload.get('request', {})
    if not request:
      return

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

    self._ParseComputeInstancesInsert(request, timesketch_record)

  def _ParseJSONPayload(self,
      json_payload: Dict[str, Any],
      timesketch_record: Dict[str, Any]) -> None:
    """Extracts information from a json_payload.

    Args:
      json_payload (dict): the contents of a GCP jsonPayload field.
      timesketch_record (dict): a dictionary that will be serialized to JSON
        and uploaded to Timesketch.
    """
    json_attributes = [
        'event_type', 'event_subtype', 'container', 'filename', 'message'
    ]
    for attribute in json_attributes:
      if attribute in json_payload:
        timesketch_record[attribute] = json_payload[attribute]

    actor = json_payload.get('actor', {})
    if actor:
      if 'user' in actor:
        timesketch_record['user'] = actor['user']

  def _BuildMessageString(self, timesketch_record: Dict[str, Any]) -> None:
    """Builds a Timesketch message string from a Timesketch record.

    Args:
      timesketch_record (dict): a dictionary that will be serialized to JSON
        and uploaded to Timesketch.
    """
    if 'message' in timesketch_record:
      return
    user = ''
    action = ''
    resource = ''

    # Ordered from least to most preferred value
    user_attributes = ['principal_email', 'user']
    for attribute in user_attributes:
      if attribute in timesketch_record:
        user = timesketch_record[attribute]

    # Ordered from least to most preferred value
    action_attributes = ['method_name', 'event_subtype']
    for attribute in action_attributes:
      if attribute in timesketch_record:
        action = timesketch_record[attribute]

    # Ordered from least to most preferred value
    resource_attributes = ['resource_label_instance_id', 'resource_name']
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

  def _ProcessLogContainer(self, logs_container: containers.File) -> None:
    """Processes a GCP logs container.

    Args:
      logs_container: container containing GCPLogsCollector output file.
    """
    if not logs_container.path:
      return

    output_file = tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', delete=False, suffix='.jsonl')
    output_path = output_file.name

    # `project_id` to be used in timeline name.
    project_id = ''

    with open(logs_container.path, 'r') as input_file:
      for line in input_file:
        transformed_line = self._ProcessLogLine(
            line, logs_container.name)
        if transformed_line:
          if not project_id:
            try:
              json_transformed_line = json.loads(transformed_line)
              project_id = json_transformed_line.get('project_id', '')
            except json.decoder.JSONDecodeError:
              pass

          output_file.write(transformed_line)
          output_file.write('\n')
    output_file.close()

    current_timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    timeline_name = f'{project_id}_{current_timestamp}'

    container = containers.File(name=timeline_name, path=output_path)
    self.StoreContainer(container)

  def Process(self) -> None:
    """Processes GCP logs containers for insertion into Timesketch."""
    for file_container in self.GetContainers(containers.File, pop=True):
      self._ProcessLogContainer(file_container)


modules_manager.ModulesManager.RegisterModule(GCPLoggingTimesketch)
