# -*- coding: utf-8 -*-
"""Definition of modules for collecting data from GRR hosts."""

from __future__ import print_function
from __future__ import unicode_literals

import datetime
import os
import re
import time
import threading
import zipfile

from grr_api_client import errors as grr_errors
from grr_response_proto import flows_pb2

from dftimewolf.lib.collectors.grr_base import GRRBaseModule
from dftimewolf.lib.errors import DFTimewolfError
from dftimewolf.lib.modules import manager as modules_manager


# TODO: GRRFlow should be extended by classes that actually implement
# the Process() method.
class GRRFlow(GRRBaseModule):  # pylint: disable=abstract-method
  """Launches and collects GRR flows.

  Modules that use GRR flows or interact with hosts should extend this class.
  """
  _CHECK_APPROVAL_INTERVAL_SEC = 10
  _CHECK_FLOW_INTERVAL_SEC = 10

  _CLIENT_ID_REGEX = re.compile(r'^c\.[0-9a-f]{16}$', re.IGNORECASE)

  def __init__(self, state):
    """Sets the keepalive attribute to False for GRRFlow objects."""
    super(GRRFlow, self).__init__(state)
    self.keepalive = False

  def _get_client_by_hostname(self, hostname):
    """Search GRR by hostname and get the latest active client.

    Args:
      hostname: hostname to search for.

    Returns:
      GRR API Client object

    Raises:
      DFTimewolfError: if no client ID found for hostname.
    """
    # Search for the hostname in GRR
    print('Searching for client: {0:s}'.format(hostname))
    try:
      search_result = self.grr_api.SearchClients(hostname)
    except grr_errors.UnknownError as exception:
      self.state.add_error('Could not search for host {0:s}: {1!s}'.format(
          hostname, exception
      ), critical=True)
      return None

    result = []
    for client in search_result:
      if hostname.lower() in client.data.os_info.fqdn.lower():
        result.append((client.data.last_seen_at, client))

    if not result:
      self.state.add_error(
          'Could not get client_id for {0:s}'.format(hostname), critical=True)
      return None

    last_seen, client = sorted(result, key=lambda x: x[0], reverse=True)[0]
    # Remove microseconds and create datetime object
    last_seen_datetime = datetime.datetime.utcfromtimestamp(
        last_seen / 1000000)
    # Timedelta between now and when the client was last seen, in minutes.
    # First, count total seconds. This will return a float.
    last_seen_seconds = (
        datetime.datetime.utcnow() - last_seen_datetime).total_seconds()
    last_seen_minutes = int(round(last_seen_seconds / 60))

    print('{0:s}: Found active client'.format(client.client_id))
    print('Found active client: {0:s}'.format(client.client_id))
    print('Client last seen: {0:s} ({1:d} minutes ago)'.format(
        last_seen_datetime.strftime('%Y-%m-%dT%H:%M:%S+0000'),
        last_seen_minutes))

    return client

  def find_clients(self, hosts):
    """Finds GRR clients given a list of hosts.

    Args:
      hosts: List of hostname FQDNs

    Returns:
      List of GRR client objects.
    """
    # TODO(tomchop): Thread this
    clients = []
    for host in hosts:
      clients.append(self._get_client_by_hostname(host))
    return [client for client in clients if client is not None]

  def _get_client_by_id(self, client_id):
    """Get GRR client dictionary and make sure valid approvals exist.

    Args:
      client_id: GRR client ID.

    Returns:
      GRR API Client object
    """
    client = self.grr_api.Client(client_id)
    print('Checking for client approval')
    self._check_approval_wrapper(client, client.ListFlows)
    print('{0:s}: Client approval is valid'.format(client_id))
    return client.Get()

  def _launch_flow(self, client, name, args):
    """Create specified flow, setting KeepAlive if requested.

    Args:
      client: GRR Client object on which to launch the flow.
      name: string containing flow name.
      args: proto (*FlowArgs) for type of flow, as defined in GRR flow proto.

    Returns:
      string containing ID of launched flow
    """
    # Start the flow and get the flow ID
    flow = self._check_approval_wrapper(
        client, client.CreateFlow, name=name, args=args)
    flow_id = flow.flow_id
    print('{0:s}: Scheduled'.format(flow_id))

    if self.keepalive:
      keepalive_flow = client.CreateFlow(
          name='KeepAlive', args=flows_pb2.KeepAliveArgs())
      print('KeepAlive Flow:{0:s} scheduled'.format(keepalive_flow.flow_id))

    return flow_id

  def _await_flow(self, client, flow_id):
    """Awaits flow completion.

    Args:
      client: GRR Client object in which to await the flow.
      flow_id: string containing ID of flow to await.

    Raises:
      DFTimewolfError: if flow error encountered.
    """
    # Wait for the flow to finish
    print('{0:s}: Waiting to finish'.format(flow_id))
    while True:
      try:
        status = client.Flow(flow_id).Get().data
      except grr_errors.UnknownError:
        msg = 'Unable to stat flow {0:s} for host {1:s}'.format(
            flow_id, client.data.os_info.fqdn.lower())
        self.state.add_error(msg)
        raise DFTimewolfError(
            'Unable to stat flow {0:s} for host {1:s}'.format(
                flow_id, client.data.os_info.fqdn.lower()))

      if status.state == flows_pb2.FlowContext.ERROR:
        # TODO(jbn): If one artifact fails, what happens? Test.
        message = status.context.backtrace
        if 'ArtifactNotRegisteredError' in status.context.backtrace:
          message = status.context.backtrace.split('\n')[-2]
        raise DFTimewolfError(
            '{0:s}: FAILED! Message from GRR:\n{1:s}'.format(
                flow_id, message))

      if status.state == flows_pb2.FlowContext.TERMINATED:
        print('{0:s}: Complete'.format(flow_id))
        break
      time.sleep(self._CHECK_FLOW_INTERVAL_SEC)

  def _download_files(self, client, flow_id):
    """Download files from the specified flow.

    Args:
      client: GRR Client object to which to download flow data from.
      flow_id: GRR flow ID.

    Returns:
      str: path of downloaded files.
    """
    output_file_path = os.path.join(
        self.output_path, '.'.join((flow_id, 'zip')))

    if os.path.exists(output_file_path):
      print('{0:s} already exists: Skipping'.format(output_file_path))
      return None

    flow = client.Flow(flow_id)
    file_archive = flow.GetFilesArchive()
    file_archive.WriteToFile(output_file_path)

    # Unzip archive for processing and remove redundant zip
    fqdn = client.data.os_info.fqdn.lower()
    client_output_file = os.path.join(self.output_path, fqdn)
    if not os.path.isdir(client_output_file):
      os.makedirs(client_output_file)

    with zipfile.ZipFile(output_file_path) as archive:
      archive.extractall(path=client_output_file)
    os.remove(output_file_path)

    return client_output_file


class GRRArtifactCollector(GRRFlow):
  """Artifact collector for GRR flows.

  Attributes:
    artifacts: comma-separated list of GRR-defined artifacts.
    use_tsk: Toggle for use_tsk flag on GRR flow.
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
  """
  _DEFAULT_ARTIFACTS_LINUX = [
      'LinuxAuditLogs', 'LinuxAuthLogs', 'LinuxCronLogs', 'LinuxWtmp',
      'AllUsersShellHistory', 'ZeitgeistDatabase'
  ]

  _DEFAULT_ARTIFACTS_DARWIN = [
      'MacOSRecentItems', 'MacOSBashHistory', 'MacOSLaunchAgentsPlistFiles',
      'MacOSAuditLogFiles', 'MacOSSystemLogFiles', 'MacOSAppleSystemLogFiles',
      'MacOSMiscLogs', 'MacOSSystemInstallationTime', 'MacOSQuarantineEvents',
      'MacOSLaunchDaemonsPlistFiles', 'MacOSInstallationHistory',
      'MacOSUserApplicationLogs', 'MacOSInstallationLogFile'
  ]

  _DEFAULT_ARTIFACTS_WINDOWS = [
      'WindowsAppCompatCache', 'WindowsEventLogs', 'WindowsPrefetchFiles',
      'WindowsScheduledTasks', 'WindowsSearchDatabase',
      'WindowsSuperFetchFiles', 'WindowsSystemRegistryFiles',
      'WindowsUserRegistryFiles', 'WindowsXMLEventLogTerminalServices'
  ]

  artifact_registry = {
      'Linux': _DEFAULT_ARTIFACTS_LINUX,
      'Darwin': _DEFAULT_ARTIFACTS_DARWIN,
      'Windows': _DEFAULT_ARTIFACTS_WINDOWS
  }

  def __init__(self, state):
    super(GRRArtifactCollector, self).__init__(state)
    self.artifacts = []
    self.extra_artifacts = []
    self.hostnames = None
    self._clients = []
    self.use_tsk = False
    self.keepalive = False

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            hosts, artifacts, extra_artifacts, use_tsk,
            reason, grr_server_url, grr_username, grr_password, approvers=None,
            verify=True):
    """Initializes a GRR artifact collector.

    Args:
      hosts: Comma-separated list of hostnames to launch the flow on.
      artifacts: list of GRR-defined artifacts.
      extra_artifacts: list of GRR-defined artifacts to append.
      use_tsk: toggle for use_tsk flag on GRR flow.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_username: GRR username.
      grr_password: GRR password.
      approvers: list of GRR approval recipients.
      verify: boolean, whether to verify the GRR server's x509 certificate.
    """
    super(GRRArtifactCollector, self).SetUp(
        reason, grr_server_url, grr_username, grr_password, approvers=approvers,
        verify=verify)

    if artifacts is not None:
      self.artifacts = [item.strip() for item in artifacts.strip().split(',')]

    if extra_artifacts is not None:
      self.extra_artifacts = [item.strip() for item
                              in extra_artifacts.strip().split(',')]

    self.hostnames = [item.strip() for item in hosts.strip().split(',')]
    self.use_tsk = use_tsk

  def _process_thread(self, client):
    """Process a single GRR client.

    Args:
      client: a GRR client object.
    """
    system_type = client.data.os_info.system
    print('System type: {0:s}'.format(system_type))

    # If the list is supplied by the user via a flag, honor that.
    artifact_list = []
    if self.artifacts:
      print('Artifacts to be collected: {0!s}'.format(self.artifacts))
      artifact_list = self.artifacts
    else:
      default_artifacts = self.artifact_registry.get(system_type, None)
      if default_artifacts:
        print('Collecting default artifacts for {0:s}: {1:s}'.format(
            system_type, ', '.join(default_artifacts)))
        artifact_list.extend(default_artifacts)

    if self.extra_artifacts:
      print('Throwing in an extra {0!s}'.format(self.extra_artifacts))
      artifact_list.extend(self.extra_artifacts)
      artifact_list = list(set(artifact_list))

    if not artifact_list:
      return

    flow_args = flows_pb2.ArtifactCollectorFlowArgs(
        artifact_list=artifact_list,
        use_tsk=self.use_tsk,
        ignore_interpolation_errors=True,
        apply_parsers=False)
    flow_id = self._launch_flow(client, 'ArtifactCollectorFlow', flow_args)
    self._await_flow(client, flow_id)
    collected_flow_data = self._download_files(client, flow_id)
    if collected_flow_data:
      print('{0!s}: Downloaded: {1:s}'.format(flow_id, collected_flow_data))
      fqdn = client.data.os_info.fqdn.lower()
      self.state.output.append((fqdn, collected_flow_data))

  def Process(self):
    """Collects artifacts from a host with GRR.

    Raises:
      DFTimewolfError: if no artifacts specified nor resolved by platform.
    """
    threads = []
    for client in self.find_clients(self.hostnames):
      print(client)
      thread = threading.Thread(target=self._process_thread, args=(client, ))
      threads.append(thread)
      thread.start()

    for thread in threads:
      thread.join()


class GRRFileCollector(GRRFlow):
  """File collector for GRR flows.

  Attributes:
    files: list of file paths.
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
  """

  def __init__(self, state):
    super(GRRFileCollector, self).__init__(state)
    self.files = []
    self.hostnames = None
    self._clients = []
    self.use_tsk = False
    self.keepalive = False

  # pylint: disable=arguments-differ
  def SetUp(self,
            hosts, files, use_tsk,
            reason, grr_server_url, grr_username, grr_password, approvers=None,
            verify=True):
    """Initializes a GRR file collector.

    Args:
      hosts: Comma-separated list of hostnames to launch the flow on.
      files: list of file paths.
      use_tsk: toggle for use_tsk flag on GRR flow.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_username: GRR username.
      grr_password: GRR password.
      approvers: list of GRR approval recipients.
      verify: boolean, whether to verify the GRR server's x509 certificate.
    """
    super(GRRFileCollector, self).SetUp(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify)

    if files is not None:
      self.files = [item.strip() for item in files.strip().split(',')]

    self.hostnames = [item.strip() for item in hosts.strip().split(',')]
    self.use_tsk = use_tsk

  def _process_thread(self, client):
    """Process a single client.

    Args:
      client: GRR client object to act on.
    """
    file_list = self.files
    if not file_list:
      return
    print('Filefinder to collect {0:d} items'.format(len(file_list)))

    flow_action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.DOWNLOAD)
    flow_args = flows_pb2.FileFinderArgs(
        paths=file_list,
        action=flow_action,)
    flow_id = self._launch_flow(client, 'FileFinder', flow_args)
    self._await_flow(client, flow_id)
    collected_flow_data = self._download_files(client, flow_id)
    if collected_flow_data:
      print('{0!s}: Downloaded: {1:s}'.format(flow_id, collected_flow_data))
      fqdn = client.data.os_info.fqdn.lower()
      self.state.output.append((fqdn, collected_flow_data))

  def Process(self):
    """Collects files from a host with GRR.

    Raises:
      DFTimewolfError: if no files specified.
    """
    threads = []
    for client in self.find_clients(self.hostnames):
      thread = threading.Thread(target=self._process_thread, args=(client, ))
      threads.append(thread)
      thread.start()

    for thread in threads:
      thread.join()


class GRRFlowCollector(GRRFlow):
  """Flow collector.

  Attributes:
    output_path: Path to where to store collected items.
    grr_api: GRR HTTP API client.
    host: Target of GRR collection.
    flow_id: ID of GRR flow to retrieve.
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
  """

  def __init__(self, state):
    super(GRRFlowCollector, self).__init__(state)
    self.client_id = None
    self.flow_id = None
    self.host = None

  # pylint: disable=arguments-differ
  def SetUp(self,
            host, flow_id,
            reason, grr_server_url, grr_username, grr_password, approvers=None,
            verify=True):
    """Initializes a GRR flow collector.

    Args:
      host: hostname of machine.
      flow_id: ID of GRR flow to retrieve.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_username: GRR username.
      grr_password: GRR password.
      approvers: list of GRR approval recipients.
      verify: boolean, whether to verify the GRR server's x509 certificate.
    """
    super(GRRFlowCollector, self).SetUp(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify)
    self.flow_id = flow_id
    self.host = host

  def Process(self):
    """Downloads the results of a GRR collection flow.

    Raises:
      DFTimewolfError: if no files specified
    """
    client = self._get_client_by_hostname(self.host)
    self._await_flow(client, self.flow_id)
    collected_flow_data = self._download_files(client, self.flow_id)
    if collected_flow_data:
      print('{0:s}: Downloaded: {1:s}'.format(
          self.flow_id, collected_flow_data))
      fqdn = client.data.os_info.fqdn.lower()
      self.state.output.append((fqdn, collected_flow_data))


modules_manager.ModulesManager.RegisterModules([
    GRRArtifactCollector, GRRFileCollector, GRRFlowCollector])
