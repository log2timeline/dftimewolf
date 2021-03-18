# -*- coding: utf-8 -*-
"""Definition of modules for collecting data from GRR hosts."""

import datetime
import os
import re
import threading
import time
import zipfile

from grr_api_client import errors as grr_errors
from grr_response_proto import flows_pb2, timeline_pb2

from dftimewolf.lib.collectors.grr_base import GRRBaseModule
from dftimewolf.lib.containers import containers
from dftimewolf.lib.errors import DFTimewolfError
from dftimewolf.lib.modules import manager as modules_manager


# TODO: GRRFlow should be extended by classes that actually implement
# the Process() method.
class GRRFlow(GRRBaseModule):  # pylint: disable=abstract-method
  """Launches and collects GRR flows.

  Modules that use GRR flows or interact with hosts should extend this class.

  Attributes:
    keepalive (bool): True if the GRR keepalive functionality should be used.
  """
  _CHECK_APPROVAL_INTERVAL_SEC = 10
  _CHECK_FLOW_INTERVAL_SEC = 10
  _MAX_OFFLINE_TIME_SEC = 3600  # One hour

  _CLIENT_ID_REGEX = re.compile(r'^c\.[0-9a-f]{16}$', re.IGNORECASE)

  def __init__(self, state, name=None, critical=False):
    """Initializes a GRR flow module.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GRRFlow, self).__init__(state, name=name, critical=critical)
    self.keepalive = False
    self._skipped_flows = []
    self.skip_offline_clients = False

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(
      self, reason, grr_server_url, grr_username, grr_password, approvers=None,
      verify=True, skip_offline_clients=False):
    """Initializes a GRR hunt result collector.

    Args:
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      approvers (Optional[str]): comma-separated GRR approval recipients.
      verify (Optional[bool]): True to indicate GRR server's x509 certificate
          should be verified.
      skip_offline_clients (Optional[bool]): Whether to wait for flows
          to complete on clients that have been offline for more than an hour.
    """
    self.skip_offline_clients = skip_offline_clients
    super(GRRFlow, self).SetUp(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify)

  def _SeenLastMonth(self, timestamp):
    """Take a UTC timestamp and check if it is in the last month.

    Args:
      timestamp (int): A timestamp in microseconds.

    Returns:
      boolean: True if the timestamp is in last month from now.
    """
    last_seen_datetime = datetime.datetime.utcfromtimestamp(
        timestamp / 1000000)
    # 30 days before now()
    month_ago = datetime.datetime.utcnow() - datetime.timedelta(30)
    return  last_seen_datetime > month_ago

  def _FilterActiveClients(self, result):
    """Take a list of clients and return clients active last month.

    Args:
      result list[tuple[int, grr_api_client.client]]: A list of tuples
          storing the last seen timestamps and client objects.

    Returns:
      list[tuple[int, grr_api_client.client]]: A list of tuples
          storing the last seen timestamps and client objects.
    """
    active_clients = list(filter(lambda x: self._SeenLastMonth(x[0]), result))
    return active_clients

  # TODO: change object to more specific GRR type information.
  def _GetClientBySelector(self, selector):
    """Searches GRR by selector and get the latest active client.

    Args:
      selector (str): selector to search for. This can be a hostname or GRR
          client ID.

    Returns:
      object: GRR API Client object

    Raises:
      DFTimewolfError: if no client ID found for selector.
    """
    # Search for the selector in GRR
    self.logger.info('Searching for client: {0:s}'.format(selector))
    try:
      search_result = self.grr_api.SearchClients(selector)
    except grr_errors.UnknownError as exception:
      self.ModuleError('Could not search for host {0:s}: {1!s}'.format(
          selector, exception
      ), critical=True)

    result = []
    for client in search_result:
      fqdn = client.data.os_info.fqdn.lower()
      client_id = client.data.client_id.lower()
      if selector.lower() in fqdn or selector.lower() in client_id:
        result.append((client.data.last_seen_at, client))

    if not result:
      self.ModuleError('Could not get client for {0:s}'.format(
          selector), critical=True)

    active_clients = self._FilterActiveClients(result)
    if len(active_clients) >1:
      self.ModuleError(
            'Multiple hosts ({0:d}) with the same '
            'FQDN: "{1:s}" have been active in the last month.\n'
            'Please use client ID instead of the hostname.'.format(
                len(active_clients), selector), critical=True)
    if not active_clients:
      self.ModuleError(
            '{0:d} inactive/old clients were found '
            'for selector: "{1:s}", non of them '
            'has been active in the last 30 days.'.format(
                len(result), selector), critical=True)

    last_seen, client = active_clients[0]
    # Remove microseconds and create datetime object
    last_seen_datetime = datetime.datetime.utcfromtimestamp(
        last_seen / 1000000)
    # Timedelta between now and when the client was last seen, in minutes.
    # First, count total seconds. This will return a float.
    last_seen_seconds = (
        datetime.datetime.utcnow() - last_seen_datetime).total_seconds()
    last_seen_minutes = int(round(last_seen_seconds / 60))

    self.logger.info('{0:s}: Found active client'.format(client.client_id))
    self.logger.info('Found active client: {0:s}'.format(client.client_id))
    self.logger.info('Client last seen: {0:s} ({1:d} minutes ago)'.format(
        last_seen_datetime.strftime('%Y-%m-%dT%H:%M:%S+0000'),
        last_seen_minutes))

    return client

  # TODO: change object to more specific GRR type information.
  def _FindClients(self, selectors):
    """Finds GRR clients given a list of selectors.

    Args:
      selectors (list[str]): FQDNs or client IDs to search for.

    Returns:
      list[object]: GRR client objects.
    """
    # TODO(tomchop): Thread this
    clients = []
    for selector in selectors:
      client = self._GetClientBySelector(selector)
      if client is not None:
        clients.append(client)
    return clients

  # TODO: change object to more specific GRR type information.
  def _LaunchFlow(self, client, name, args):
    """Creates the specified flow, setting KeepAlive if requested.

    Args:
      client (object): GRR Client object on which to launch the flow.
      name (str): name of the GRR flow.
      args (object): arguments specific for type of flow, as defined in GRR
          flow proto (FlowArgs).

    Returns:
      str: GRR identifier for launched flow, or an empty string if flow could
          not be launched.
    """
    # Start the flow and get the flow ID
    flow = self._WrapGRRRequestWithApproval(
        client, client.CreateFlow, name=name, args=args)
    if not flow:
      return ''

    flow_id = flow.flow_id
    self.logger.info('{0:s}: Scheduled'.format(flow_id))

    if self.keepalive:
      keepalive_flow = client.CreateFlow(
          name='KeepAlive', args=flows_pb2.KeepAliveArgs())
      self.logger.info(
          'KeepAlive Flow:{0:s} scheduled'.format(keepalive_flow.flow_id))

    return flow_id

  # TODO: change object to more specific GRR type information.
  def _AwaitFlow(self, client, flow_id):
    """Waits for a specific GRR flow to complete.

    Args:
      client (object): GRR Client object in which to await the flow.
      flow_id (str): GRR identifier of the flow to await.

    Raises:
      DFTimewolfError: If a Flow error was encountered.
    """
    self.logger.info('{0:s}: Waiting to finish'.format(flow_id))
    if self.skip_offline_clients:
      self.logger.info('Client will be skipped if offline.')

    while True:
      try:
        status = client.Flow(flow_id).Get().data
      except grr_errors.UnknownError:
        msg = 'Unable to stat flow {0:s} for host {1:s}'.format(
            flow_id, client.data.os_info.fqdn.lower())
        self.ModuleError(msg, critical=True)

      if status.state == flows_pb2.FlowContext.ERROR:
        # TODO(jbn): If one artifact fails, what happens? Test.
        message = status.context.backtrace
        if 'ArtifactNotRegisteredError' in status.context.backtrace:
          message = status.context.backtrace.split('\n')[-2]
        raise DFTimewolfError(
            '{0:s}: FAILED! Message from GRR:\n{1:s}'.format(
                flow_id, message))

      if status.state == flows_pb2.FlowContext.TERMINATED:
        self.logger.info('{0:s}: Complete'.format(flow_id))
        break

      time.sleep(self._CHECK_FLOW_INTERVAL_SEC)
      if not self.skip_offline_clients:
        continue

      client_last_seen = datetime.datetime.fromtimestamp(
          client.data.last_seen_at / 1000000, datetime.timezone.utc)
      now = datetime.datetime.now(datetime.timezone.utc)
      if (now - client_last_seen).total_seconds() > self._MAX_OFFLINE_TIME_SEC:
        self.logger.warning(
              'Client {0:s} has been offline for more than {1:.1f} minutes'
              ', skipping...'.format(
                  client.client_id, self._MAX_OFFLINE_TIME_SEC / 60))
        self._skipped_flows.append((client.client_id, flow_id))
        break

  def _CheckSkippedFlows(self):
    if not self._skipped_flows:
      return

    self.logger.warning(
        'Skipped waiting for {0:d} flows because hosts were offline'.format(
            len(self._skipped_flows)))
    self.logger.warning(
      'Run the grr_flow_collect recipe with --wait_for_offline_hosts in a'
      ' tmux shell'
    )
    for client_id, flow_id in self._skipped_flows:
      self.logger.warning(
          'dftimewolf grr_flow_collect {0:s} {1:s} {2:s} /tmp/directory'.format(
              client_id, flow_id, self.reason
        ))

  # TODO: change object to more specific GRR type information.
  def _DownloadFiles(self, client, flow_id):
    """Download files from the specified flow.

    Args:
      client (object): GRR Client object to which to download flow data from.
      flow_id (str): GRR identifier of the flow.

    Returns:
      str: path of downloaded files.
    """
    output_file_path = os.path.join(
        self.output_path, '.'.join((flow_id, 'zip')))

    if os.path.exists(output_file_path):
      self.logger.info(
          '{0:s} already exists: Skipping'.format(output_file_path))
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
    artifacts (list[str]): artifact definition names.
    extra_artifacts (list[str]): extra artifact definition names.
    hostnames (list[str]): FDQNs of the GRR client hosts.
    use_tsk (bool): True if GRR should use Sleuthkit (TSK) to collect file
        system artifacts.
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

  def __init__(self, state, name=None, critical=False):
    super(GRRArtifactCollector, self).__init__(
        state, name=name, critical=critical)
    self._clients = []
    self.artifacts = []
    self.extra_artifacts = []
    self.hostnames = None
    self.use_tsk = False

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            hosts, artifacts, extra_artifacts, use_tsk,
            reason, grr_server_url, grr_username, grr_password, approvers=None,
            verify=True, skip_offline_clients=False):
    """Initializes a GRR artifact collector.

    Args:
      hosts (str): comma-separated hostnames to launch the flow on.
      artifacts (str): comma-separated artifact definition names.
      extra_artifacts (str): comma-separated extra artifact definition names.
      use_tsk (bool): True if GRR should use Sleuthkit (TSK) to collect file
          system artifacts.
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      approvers (Optional[str]): list of GRR approval recipients.
      verify (Optional[bool]): True to indicate GRR server's x509 certificate
          should be verified.
      skip_offline_clients (Optional[bool]): Whether to wait for flows
          to complete on clients that have been offline for more than an hour.
    """
    super(GRRArtifactCollector, self).SetUp(
        reason, grr_server_url, grr_username, grr_password, approvers=approvers,
        verify=verify, skip_offline_clients=skip_offline_clients)

    if artifacts is not None:
      self.artifacts = [item.strip() for item in artifacts.strip().split(',')]

    if extra_artifacts is not None:
      self.extra_artifacts = [item.strip() for item
                              in extra_artifacts.strip().split(',')]

    self.hostnames = [item.strip() for item in hosts.strip().split(',')]
    self.use_tsk = use_tsk

  # TODO: change object to more specific GRR type information.
  def _ProcessThread(self, client):
    """Processes a single GRR client.

    This function is used as a callback for the processing thread.

    Args:
      client (object): a GRR client object.
    """
    system_type = client.data.os_info.system
    self.logger.info('System type: {0:s}'.format(system_type))

    # If the list is supplied by the user via a flag, honor that.
    artifact_list = []
    if self.artifacts:
      self.logger.info(
          'Artifacts to be collected: {0!s}'.format(self.artifacts))
      artifact_list = self.artifacts
    else:
      default_artifacts = self.artifact_registry.get(system_type, None)
      if default_artifacts:
        self.logger.info('Collecting default artifacts for {0:s}: {1:s}'.format(
            system_type, ', '.join(default_artifacts)))
        artifact_list.extend(default_artifacts)

    if self.extra_artifacts:
      self.logger.info(
          'Throwing in an extra {0!s}'.format(self.extra_artifacts))
      artifact_list.extend(self.extra_artifacts)
      artifact_list = list(set(artifact_list))

    if not artifact_list:
      return

    flow_args = flows_pb2.ArtifactCollectorFlowArgs(
        artifact_list=artifact_list,
        use_tsk=self.use_tsk,
        ignore_interpolation_errors=True,
        apply_parsers=False)
    flow_id = self._LaunchFlow(client, 'ArtifactCollectorFlow', flow_args)
    if not flow_id:
      msg = 'Flow could not be launched on {0:s}.'.format(client.client_id)
      msg += '\nArtifactCollectorFlow args: {0!s}'.format(flow_args)
      self.ModuleError(msg, critical=True)
    self._AwaitFlow(client, flow_id)
    collected_flow_data = self._DownloadFiles(client, flow_id)

    if collected_flow_data:
      self.logger.info(
          '{0!s}: Downloaded: {1:s}'.format(flow_id, collected_flow_data))
      container = containers.File(
          name=client.data.os_info.fqdn.lower(),
          path=collected_flow_data
      )
      self.state.StoreContainer(container)

  def Process(self):
    """Collects artifacts from a host with GRR.

    Raises:
      DFTimewolfError: if no artifacts specified nor resolved by platform.
    """
    threads = []
    for client in self._FindClients(self.hostnames):
      thread = threading.Thread(target=self._ProcessThread, args=(client, ))
      threads.append(thread)
      thread.start()

    for thread in threads:
      thread.join()


class GRRFileCollector(GRRFlow):
  """File collector for GRR flows.

  Attributes:
    files (list[str]): file paths.
    hostnames (list[str]): FDQNs of the GRR client hosts.
    use_tsk (bool): True if GRR should use Sleuthkit (TSK) to collect files.
    action (FileFinderAction): Enum denoting action to take.
  """
  _ACTIONS = {'download': flows_pb2.FileFinderAction.DOWNLOAD,
              'hash': flows_pb2.FileFinderAction.HASH,
              'stat': flows_pb2.FileFinderAction.STAT,
             }

  def __init__(self, state, name=None, critical=False):
    super(GRRFileCollector, self).__init__(state, name=name, critical=critical)
    self._clients = []
    self.files = []
    self.hostnames = None
    self.use_tsk = False
    self.action = None

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            hosts, files, use_tsk,
            reason, grr_server_url, grr_username, grr_password, approvers=None,
            verify=True, skip_offline_clients=False, action='download'):
    """Initializes a GRR file collector.

    Args:
      hosts (str): comma-separated hostnames to launch the flow on.
      files (str): comma-separated file paths.
      use_tsk (bool): True if GRR should use Sleuthkit (TSK) to collect files.
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      approvers (Optional[str]): list of GRR approval recipients.
      verify (Optional[bool]): True to indicate GRR server's x509 certificate
          should be verified.
      skip_offline_clients (Optional[bool]): Whether to wait for flows
          to complete on clients that have been offline for more than an hour.
      action (Optional[str]): Action (download/hash/stat) (default: download).
    """
    super(GRRFileCollector, self).SetUp(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify,
        skip_offline_clients=skip_offline_clients)

    if files is not None:
      self.files = [item.strip() for item in files.strip().split(',')]

    self.hostnames = [item.strip() for item in hosts.strip().split(',')]
    self.use_tsk = use_tsk

    if action.lower() in self._ACTIONS:
      self.action = self._ACTIONS[action.lower()]
    if self.action is None:
      self.ModuleError("Invalid action {0!s}".format(action),
                       critical=True)

  # TODO: change object to more specific GRR type information.
  def _ProcessThread(self, client):
    """Processes a single client.

    This function is used as a callback for the processing thread.

    Args:
      client (object): GRR client object to act on.
    """
    file_list = self.files
    if not file_list:
      return
    self.logger.info('Filefinder to collect {0:d} items'.format(len(file_list)))

    flow_action = flows_pb2.FileFinderAction(
        action_type=self.action)
    flow_args = flows_pb2.FileFinderArgs(
        paths=file_list,
        action=flow_action,)
    flow_id = self._LaunchFlow(client, 'FileFinder', flow_args)
    self._AwaitFlow(client, flow_id)
    collected_flow_data = self._DownloadFiles(client, flow_id)
    if collected_flow_data:
      self.logger.info(
          '{0!s}: Downloaded: {1:s}'.format(flow_id, collected_flow_data))
      container = containers.File(
          name=client.data.os_info.fqdn.lower(),
          path=collected_flow_data
      )
      self.state.StoreContainer(container)

  def Process(self):
    """Collects files from a host with GRR.

    Raises:
      DFTimewolfError: if no files specified.
    """
    threads = []
    for client in self._FindClients(self.hostnames):
      thread = threading.Thread(target=self._ProcessThread, args=(client, ))
      threads.append(thread)
      thread.start()

    for thread in threads:
      thread.join()

    self._CheckSkippedFlows()

class GRRFlowCollector(GRRFlow):
  """Flow collector.

  Attributes:
    client_id (str): GRR identifier of the client.
    flow_id (str): GRR identifier of the flow to retrieve.
    host (str): Target of GRR collection.
  """

  def __init__(self, state, name=None, critical=False):
    super(GRRFlowCollector, self).__init__(state, name=name, critical=critical)
    self.client_id = None
    self.flow_id = None
    self.host = None

  # pylint: disable=arguments-differ
  def SetUp(self,
            host, flow_id,
            reason, grr_server_url, grr_username, grr_password, approvers=None,
            verify=True, skip_offline_clients=False):
    """Initializes a GRR flow collector.

    Args:
      host (str): hostname of machine.
      flow_id (str): GRR identifier of the flow to retrieve.
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      approvers (Optional[str]): list of GRR approval recipients.
      verify (Optional[bool]): True to indicate GRR server's x509 certificate
          should be verified.
      skip_offline_clients (Optional[bool]): Whether to wait for flows
          to complete on clients that have been offline for more than an hour.
    """
    super(GRRFlowCollector, self).SetUp(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify,
        skip_offline_clients=skip_offline_clients)

    self.flow_id = flow_id
    self.host = host

  def Process(self):
    """Downloads the results of a GRR collection flow.

    Raises:
      DFTimewolfError: if no files specified
    """
    # TODO (tomchop): Change the host attribute into something more appropriate
    # like 'selectors', and the corresponding recipes.
    client = self._GetClientBySelector(self.host)
    self._AwaitFlow(client, self.flow_id)
    self._CheckSkippedFlows()
    collected_flow_data = self._DownloadFiles(client, self.flow_id)
    if collected_flow_data:
      self.logger.info('{0:s}: Downloaded: {1:s}'.format(
          self.flow_id, collected_flow_data))
      container = containers.File(
          name=client.data.os_info.fqdn.lower(),
          path=collected_flow_data
      )
      self.state.StoreContainer(container)


class GRRTimelineCollector(GRRFlow):
  """Timeline collector for GRR flows.

  Attributes:
    root_path (str): root path.
    hostnames (list[str]): FDQNs of the GRR client hosts.
  """

  def __init__(self, state, name=None, critical=False):
    super(GRRTimelineCollector, self).__init__(
        state, name=name, critical=critical)
    self._clients = []
    self.root_path = None
    self.hostnames = None
    self._timeline_format = None

  # We're overriding the behavior of GRRFlow's SetUp function to include new
  # parameters.
  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            hosts, root_path,
            reason, timeline_format, grr_server_url, grr_username, grr_password,
            approvers=None, verify=True, skip_offline_clients=False):
    """Initializes a GRR timeline collector.
    Args:
      hosts (str): comma-separated hostnames to launch the flow on.
      root_path (str): path to start the recursive timeline.
      reason (str): justification for GRR access.
      timeline_format (str): Timeline format (1 is BODY, 2 is RAW).
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      approvers (Optional[str]): list of GRR approval recipients.
      verify (Optional[bool]): True to indicate GRR server's x509 certificate
          should be verified.
      skip_offline_clients (Optional[bool]): Whether to wait for flows
          to complete on clients that have been offline for more than an hour.
    """
    super(GRRTimelineCollector, self).SetUp(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify,
        skip_offline_clients=skip_offline_clients)

    if root_path is not None:
      self.root_path = root_path.strip()

    self.hostnames = [item.strip() for item in hosts.strip().split(',')]
    self._timeline_format = int(timeline_format)
    self.root_path = root_path.encode()
    if self._timeline_format not in [1, 2]:
      self.ModuleError('Timeline format must be 1 (BODY) or 2 (RAW).',
                       critical=True)

  # TODO: change object to more specific GRR type information.
  def _ProcessThread(self, client):
    """Processes a single client.
    This function is used as a callback for the processing thread.
    Args:
      client (object): GRR client object to act on.
    """
    root_path = self.root_path
    if not root_path:
      return
    self.logger.info(
        'Timeline to start from "{0:s}" items'.format(root_path.decode()))

    timeline_args = timeline_pb2.TimelineArgs(root=root_path,)
    flow_id = self._LaunchFlow(client, 'TimelineFlow', timeline_args)
    self._AwaitFlow(client, flow_id)
    collected_flow_data = self._DownloadTimeline(client, flow_id)
    if collected_flow_data:
      self.logger.info(
          '{0!s}: Downloaded: {1:s}'.format(flow_id, collected_flow_data))
      container = containers.File(
          name=client.data.os_info.fqdn.lower(),
          path=collected_flow_data
      )
      self.state.StoreContainer(container)

  def Process(self):
    """Collects a timeline from a host with GRR.
    Raises:
      DFTimewolfError: if no files specified.
    """
    threads = []
    for client in self._FindClients(self.hostnames):
      thread = threading.Thread(target=self._ProcessThread, args=(client, ))
      threads.append(thread)
      thread.start()

    for thread in threads:
      thread.join()
    self._CheckSkippedFlows()

  def _DownloadTimeline(self, client, flow_id):
    """Download a timeline in BODY format from the specified flow.
    Args:
      client (object): GRR Client object to which to download flow data from.
      flow_id (str): GRR identifier of the flow.
    Returns:
      str: path of downloaded files.
    """
    extension = 'body' if self._timeline_format == 1 else 'raw'
    output_file_path = os.path.join(
        self.output_path, '.'.join((flow_id, extension)))

    if os.path.exists(output_file_path):
      self.logger.info(
          '{0:s} already exists: Skipping'.format(output_file_path))
      return None

    flow = client.Flow(flow_id)
    if self._timeline_format == 1:
      ntfs_inodes = client.data.os_info.lower() == 'windows'
      timeline = flow.GetCollectedTimelineBody(
          timestamp_subsecond_precision=True,
          inode_ntfs_file_reference_format=ntfs_inodes,
          backslash_escape=True)
    else:
      timeline = flow.GetCollectedTimeline(self._timeline_format)
    timeline.WriteToFile(output_file_path)

    return output_file_path


modules_manager.ModulesManager.RegisterModules([
    GRRArtifactCollector,
    GRRFileCollector,
    GRRFlowCollector,
    GRRTimelineCollector])
