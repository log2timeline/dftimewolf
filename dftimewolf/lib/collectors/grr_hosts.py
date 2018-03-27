"""Definition of modules for collecting data from GRR hosts."""

from __future__ import unicode_literals

import datetime
import os
import re
import time
import zipfile

from dftimewolf.lib.collectors.grr_base import GRRBaseModule

from grr_api_client import errors as grr_errors
from grr_response_proto import flows_pb2


# GRRFlow should be extended by classes that actually implement the process()
# method
class GRRFlow(GRRBaseModule):  # pylint: disable=abstract-method
  """Launches and collects GRR flows.

  Modules that use GRR flows or interact with hosts should extend this class.
  """
  _CHECK_APPROVAL_INTERVAL_SEC = 10
  _CHECK_FLOW_INTERVAL_SEC = 10

  _CLIENT_ID_REGEX = re.compile(r'^c\.[0-9a-f]{16}$', re.IGNORECASE)

  def _get_client_by_hostname(self, hostname):
    """Search GRR by hostname and get the latest active client.

    Args:
      hostname: hostname to search for.

    Returns:
      GRR API Client object

    Raises:
      RuntimeError: if no client ID found for hostname.
    """
    if self._CLIENT_ID_REGEX.match(hostname):
      return hostname

    # Search for the hostname in GRR
    print 'Searching for client: {0:s}'.format(hostname)
    search_result = self.grr_api.SearchClients(hostname)

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
    last_seen_minutes = int(round(last_seen_seconds)) / 60

    print '{0:s}: Found active client'.format(client.client_id)
    print 'Found active client: {0:s}'.format(client.client_id)
    print 'Client last seen: {0:s} ({1:d} minutes ago)'.format(
        last_seen_datetime.strftime('%Y-%m-%dT%H:%M:%S+0000'),
        last_seen_minutes)

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
    return clients

  def _get_client_by_id(self, client_id):
    """Get GRR client dictionary and make sure valid approvals exist.

    Args:
      client_id: GRR client ID.

    Returns:
      GRR API Client object
    """
    client = self.grr_api.Client(client_id)
    print 'Checking for client approval'
    self._check_approval_wrapper(client, client.ListFlows)
    print '{0:s}: Client approval is valid'.format(client_id)
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
    flow = client.CreateFlow(name=name, args=args)
    flow_id = flow.flow_id
    print '{0:s}: Scheduled'.format(flow_id)

    if self.keepalive:
      keepalive_flow = client.CreateFlow(
          name='KeepAlive', args=flows_pb2.KeepAliveArgs())
      print 'KeepAlive Flow:{0:s} scheduled'.format(keepalive_flow.flow_id)

    return flow_id

  def _await_flow(self, client, flow_id):
    """Awaits flow completion.

    Args:
      client: GRR Client object in which to await the flow.
      flow_id: string containing ID of flow to await.

    Raises:
      RuntimeError: if flow error encountered.
    """
    # Wait for the flow to finish
    print '{0:s}: Waiting to finish'.format(flow_id)
    while True:
      try:
        status = client.Flow(flow_id).Get().data
      except grr_errors.UnknownError:
        msg = 'Unable to stat flow {0:s} for host {1:s}'.format(
            flow_id, self.host)
        self.state.add_error(msg)
        raise RuntimeError(
            'Unable to stat flow {0:s} for host {1:s}'.format(
                flow_id, self.host))

      if status.state == flows_pb2.FlowContext.ERROR:
        # TODO(jbn): If one artifact fails, what happens? Test.
        raise RuntimeError(
            '{0:s}: FAILED! Backtrace from GRR:\n\n{1:s}'.format(
                flow_id, status.context.backtrace))

      if status.state == flows_pb2.FlowContext.TERMINATED:
        print '{0:s}: Complete'.format(flow_id)
        break
      time.sleep(self._CHECK_FLOW_INTERVAL_SEC)

    # Download the files collected by the flow
    print '{0:s}: Downloading artifacts'.format(flow_id)
    collected_file_path = self._download_files(client, flow_id)

    if collected_file_path:
      print '{0:s}: Downloaded: {1:s}'.format(flow_id, collected_file_path)

  def print_status(self, flow):
    """Print status of flow.

    Args:
      flow: GRR flow to check the status for.

    Raises:
      RuntimeError: if error encountered getting flow data.
    """
    client = self._get_client_by_id(self._client_id)
    try:
      status = client.Flow(flow.flow_id).Get().data
    except grr_errors.UnknownError:
      raise RuntimeError(
          'Unable to stat flow {0:s} for client {1:s}'.format(
              flow.flow_id, client.client_id))

    code_to_msg = {
        flows_pb2.FlowContext.ERROR: 'ERROR',
        flows_pb2.FlowContext.TERMINATED: 'Complete',
        flows_pb2.FlowContext.RUNNING: 'Running...'
    }
    msg = code_to_msg[status.state]
    print 'Status of flow {0:s}: {1:s}\n'.format(flow.flow_id, msg)

  def _download_files(self, client, flow_id):
    """Download files from the specified flow.

    Args:
      client: GRR Client object to which to download flow data from.
      flow_id: GRR flow ID.

    Returns:
      str: path of downloaded files.
    """
    if not os.path.isdir(self.output_path):
      os.makedirs(self.output_path)

    output_file_path = os.path.join(
        self.output_path, '.'.join((flow_id, 'zip')))

    if os.path.exists(output_file_path):
      print '{0:s} already exists: Skipping'.format(output_file_path)
      return None

    flow = client.Flow(flow_id)
    file_archive = flow.GetFilesArchive()
    file_archive.WriteToFile(output_file_path)

    # Unzip archive for processing and remove redundant zip
    with zipfile.ZipFile(output_file_path) as archive:
      archive.extractall(path=self.output_path)
    os.remove(output_file_path)

    return output_file_path


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

  # pylint: disable=arguments-differ
  def setup(self,
            hosts, artifacts, extra_artifacts, use_tsk,
            reason, grr_server_url, grr_auth, approvers=None):
    """Initializes a GRR artifact collector.

    Args:
      hosts: Comma-separated list of hostnames to launch the flow on.
      artifacts: list of GRR-defined artifacts.
      extra_artifacts: list of GRR-defined artifacts to append.
      use_tsk: toggle for use_tsk flag on GRR flow.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      approvers: list of GRR approval recipients.
    """

    super(GRRArtifactCollector, self).setup(
        reason, grr_server_url, grr_auth, approvers=approvers)

    if artifacts is not None:
      self.artifacts = [item.strip() for item in artifacts.strip().split(',')]

    if extra_artifacts is not None:
      self.extra_artifacts = [item.strip() for item
                              in extra_artifacts.strip().split(',')]

    hosts = [item.strip() for item in hosts.strip().split(',')]
    # TODO(tomchop): Thread this
    self._clients = self.find_clients(hosts)
    self.use_tsk = use_tsk

  def process(self):
    """Collect the artifacts.

    Returns:
      list of tuples containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.

    Raises:
      RuntimeError: if no artifacts specified nor resolved by platform.
    """

    # TODO(tomchop): Thread this
    for client in self._clients:
      # Create a list of artifacts to collect.

      system_type = client.data.os_info.system
      print 'System type: {0:s}'.format(system_type)

      # If the list is supplied by the user via a flag, honor that.
      artifact_list = []
      if self.artifacts:
        print 'Artifacts to be collected: {0:s}'.format(self.artifacts)
        artifact_list = self.artifacts
      else:
        default_artifacts = self.artifact_registry.get(system_type, None)
        print 'Collecting default artifacts for {0:s}: {1:s}'.format(
            system_type, default_artifacts)
        artifact_list.extend(default_artifacts)

      if self.extra_artifacts:
        print 'Throwing in an extra {0:s}'.format(self.extra_artifacts)
        artifact_list.extend(self.extra_artifacts)
        artifact_list = list(set(artifact_list))

      if not artifact_list:
        raise RuntimeError('No artifacts to collect')

      flow_args = flows_pb2.ArtifactCollectorFlowArgs(
          artifact_list=artifact_list,
          use_tsk=self.use_tsk,
          ignore_interpolation_errors=True,
          apply_parsers=False)
      flow_id = self._launch_flow(client, 'ArtifactCollectorFlow', flow_args)
      self._await_flow(client, flow_id)

    self.state.output = [self.output_path]


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
  def setup(self,
            hosts, files, use_tsk,
            reason, grr_server_url, grr_auth, approvers=None):
    """Initializes a GRR file collector.

    Args:
      hosts: Comma-separated list of hostnames to launch the flow on.
      files: list of file paths.
      use_tsk: toggle for use_tsk flag on GRR flow.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      approvers: list of GRR approval recipients.
    """
    super(GRRFileCollector, self).setup(
        reason, grr_server_url, grr_auth, approvers=approvers)

    if files is not None:
      self.files = [item.strip() for item in files.strip().split(',')]

    hosts = [item.strip() for item in hosts.strip().split(',')]
    self._clients = self.find_clients(hosts)
    self.use_tsk = use_tsk

  def process(self):
    """Collect the files.

    Returns:
      list of tuples containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.

    Raises:
      RuntimeError: if no files specified.
    """
    # TODO(tomchop): Thread this
    for client in self._clients:
      file_list = self.files
      if not file_list:
        raise RuntimeError('File paths must be specified for FileFinder')
      print 'Filefinder to collect {0:d} items'.format(len(file_list))

      flow_action = flows_pb2.FileFinderAction(
          action_type=flows_pb2.FileFinderAction.DOWNLOAD)
      flow_args = flows_pb2.FileFinderArgs(
          paths=file_list,
          action=flow_action,)
      flow_id = self._launch_flow(client, 'FileFinder', flow_args)
      self._await_flow(client, flow_id)

    self.state.output = [self.output_path]


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
  def setup(self,
            host, flow_id,
            reason, grr_server_url, grr_auth, approvers=None):
    """Initializes a GRR flow collector.

    Args:
      host: hostname of machine.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      flow_id: ID of GRR flow to retrieve.
      approvers: list of GRR approval recipients.
      verbose: toggle for verbose output.
    """
    super(GRRFlowCollector, self).setup(
        reason, grr_server_url, grr_auth, approvers=approvers)
    self.flow_id = flow_id
    self.host = host

  def process(self):
    """Collect the results.

    Returns:
      list: containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.

    Raises:
      RuntimeError: if no files specified
    """
    client_id = self._get_client_by_hostname(self.host).client_id
    self._await_flow(self._get_client_by_id(client_id), self.flow_id)
    self.state.output.append((self.host, self.output_path))
