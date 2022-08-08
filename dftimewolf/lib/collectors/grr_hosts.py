# -*- coding: utf-8 -*-
"""Definition of modules for collecting data from GRR hosts."""

import datetime
import os
import re
import shutil
import time
import zipfile
from typing import List, Optional, Tuple, Type

import pandas as pd

from grr_api_client import errors as grr_errors
from grr_api_client.client import Client
from grr_response_proto import flows_pb2, jobs_pb2, timeline_pb2
from grr_response_proto import osquery_pb2 as osquery_flows

from dftimewolf.lib import module
from dftimewolf.lib.collectors.grr_base import GRRBaseModule
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.errors import DFTimewolfError
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


GRR_THREAD_POOL_SIZE = 10 # Arbitrary

# TODO: GRRFlow should be extended by classes that actually implement
# the Process() method.
# pylint: disable=abstract-method
class GRRFlow(GRRBaseModule, module.ThreadAwareModule):
  """Launches and collects GRR flows.

  Modules that use GRR flows or interact with hosts should extend this class.

  Attributes:
    keepalive (bool): True if the GRR keepalive functionality should be used.
  """
  _CHECK_APPROVAL_INTERVAL_SEC = 10
  _CHECK_FLOW_INTERVAL_SEC = 10
  _MAX_OFFLINE_TIME_SEC = 3600  # One hour

  _CLIENT_ID_REGEX = re.compile(r'^c\.[0-9a-f]{16}$', re.IGNORECASE)

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a GRR flow module.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    module.ThreadAwareModule.__init__(self, state, name=name, critical=critical)
    GRRBaseModule.__init__(self)
    self.keepalive = False
    self._skipped_flows = []  # type: List[Tuple[str, str]]
    self.skip_offline_clients = False

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(
      self,
      reason: str,
      grr_server_url: str,
      grr_username: str,
      grr_password: str,
      approvers: Optional[str]=None,
      verify: bool=True,
      skip_offline_clients: bool=False) -> None:
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
    self.GrrSetUp(
        reason, grr_server_url, grr_username, grr_password, approvers=approvers,
        verify=verify, message_callback=self.PublishMessage)

  def _SeenLastMonth(self, timestamp: int) -> bool:
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

  def _FilterActiveClients(
      self, result: List[Tuple[int, Client]]) -> List[Tuple[int, Client]]:
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

  def _FilterSelectionCriteria(
      self,
      selector: str,
      search_result: List[Client]) -> List[Tuple[int, Client]]:
    result = []
    selector = selector.lower()
    for client in search_result:
      fqdn_match = selector in client.data.os_info.fqdn.lower()
      client_id_match = selector in client.data.client_id.lower()
      usernames = [user.username for user in client.data.users]
      username_match = selector in usernames and len(usernames) == 1
      if fqdn_match or client_id_match or username_match:
        result.append((client.data.last_seen_at, client))
    return result

  # TODO: change object to more specific GRR type information.
  def _GetClientBySelector(self, selector: str) -> Client:
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

    result = self._FilterSelectionCriteria(selector, search_result)

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

    self.logger.info('Found active client: {0:s}'.format(client.client_id))
    self.logger.info('Client last seen: {0:s} ({1:d} minutes ago)'.format(
        last_seen_datetime.strftime('%Y-%m-%dT%H:%M:%S+0000'),
        last_seen_minutes))

    return client

  # TODO: change object to more specific GRR type information.
  def _FindClients(self, selectors: List[str]) -> List[Client]:
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
  def _LaunchFlow(self, client: Client, name: str, args: str) -> str:
    """Creates the specified flow, setting KeepAlive if requested.

    Args:
      client (object): GRR Client object on which to launch the flow.
      name (str): name of the GRR flow.
      args (object): arguments specific for type of flow, as defined in GRR
          flow proto (FlowArgs).

    Returns:
      str: GRR identifier for launched flow, or an empty string if flow could
          not be launched.

    Raises:
      DFTimewolfError: If approvers are required but none were specified.
    """
    # Start the flow and get the flow ID
    flow = self._WrapGRRRequestWithApproval(
        client, client.CreateFlow, self.logger, name=name, args=args)
    if not flow:
      return ''

    flow_id = flow.flow_id  # type: str
    self.PublishMessage(f'{flow_id}: Scheduled')

    if self.keepalive:
      keepalive_flow = client.CreateFlow(
          name='KeepAlive', args=flows_pb2.KeepAliveArgs())
      self.logger.info(
          'KeepAlive Flow:{0:s} scheduled'.format(keepalive_flow.flow_id))

    return flow_id

  # TODO: change object to more specific GRR type information.
  def _AwaitFlow(self, client: Client, flow_id: str) -> None:
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
        msg = (f'Unknown error retrieving flow {flow_id} for host '
            f'{client.data.os_info.fqdn.lower()}')
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

  def _CheckSkippedFlows(self) -> None:
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
  def _DownloadFiles(self, client: Client, flow_id: str) -> Optional[str]:
    """Download files/results from the specified flow.

    Args:
      client (object): GRR Client object to which to download flow data from.
      flow_id (str): GRR identifier of the flow.

    Returns:
      str: path containing the downloaded files.
    """
    flow = client.Flow(flow_id)
    is_timeline_flow = False
    if flow.Get().data.name == 'TimelineFlow':
      is_timeline_flow = True
      output_file_path = os.path.join(
          self.output_path, '.'.join((flow_id, 'body')))
    else:
      output_file_path = os.path.join(
          self.output_path, '.'.join((flow_id, 'zip')))

    if os.path.exists(output_file_path):
      self.logger.info(
          '{0:s} already exists: Skipping'.format(output_file_path))
      return None

    if is_timeline_flow:
      file_archive = flow.GetCollectedTimelineBody()
    else:
      file_archive = flow.GetFilesArchive()

    file_archive.WriteToFile(output_file_path)

    # Unzip archive for processing and remove redundant zip
    fqdn = client.data.os_info.fqdn.lower()
    client_output_folder = os.path.join(self.output_path, fqdn, flow_id)
    if not os.path.isdir(client_output_folder):
      os.makedirs(client_output_folder)

    if is_timeline_flow:
      shutil.copy2(
          output_file_path,
          os.path.join(client_output_folder,
                       '{}_timeline.body'.format(flow_id)))
    else:
      with zipfile.ZipFile(output_file_path) as archive:
        archive.extractall(path=client_output_folder)
    os.remove(output_file_path)

    return client_output_folder

  def GetThreadPoolSize(self) -> int:
    """Thread pool size."""
    return GRR_THREAD_POOL_SIZE


class GRRArtifactCollector(GRRFlow):
  """Artifact collector for GRR flows.

  Attributes:
    artifacts (list[str]): artifact definition names.
    extra_artifacts (list[str]): extra artifact definition names.
    hosts (list[containers.Host]): Hosts to collect artifacts from.
    use_raw_filesystem_access (bool): True if GRR should use raw disk access to
        collect file system artifacts.
  """

  _DEFAULT_ARTIFACTS_LINUX = [
      'LinuxAuditLogs', 'LinuxAuthLogs', 'LinuxCronLogs', 'LinuxWtmp',
      'ShellHistoryFile', 'ZeitgeistDatabase'
  ]

  _DEFAULT_ARTIFACTS_DARWIN = [
      'MacOSRecentItemsPlistFile', 'BashShellHistoryFile',
      'MacOSLaunchAgentsPlistFile', 'MacOSAuditLogFile', 'MacOSSystemLogFile',
      'MacOSAppleSystemLogFile', 'MacOSLogFile', 'MacOSAppleSetupDoneFile',
      'MacOSQuarantineEventsSQLiteDatabaseFile',
      'MacOSLaunchDaemonsPlistFile', 'MacOSInstallationHistoryPlistFile',
      'MacOSUserApplicationLogFile', 'MacOSInstallationLogFile'
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

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    super(GRRArtifactCollector, self).__init__(
        state, name=name, critical=critical)
    self._clients = []  # type: List[Client]
    self.artifacts = []  # type: List[str]
    self.extra_artifacts = [] # type: List[str]
    self.hosts = [] # type: List[containers.Host]
    self.use_raw_filesystem_access = False
    self.max_file_size = 5*1024*1024*1024  # 5 GB

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            hostnames: str,
            artifacts: Optional[str],
            extra_artifacts: Optional[str],
            use_raw_filesystem_access: bool,
            reason: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            max_file_size: Optional[int],
            approvers: Optional[str]=None,
            verify: bool=True,
            skip_offline_clients: bool=False) -> None:
    """Initializes a GRR artifact collector.

    Args:
      hostnames (str): comma-separated hostnames to launch the flow on.
      artifacts (str): comma-separated artifact definition names.
      extra_artifacts (str): comma-separated extra artifact definition names.
      use_raw_filesystem_access (bool): True if GRR should use raw disk access
          to collect file system artifacts.
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      max_file_size (str): Maximum file size to collect (in bytes).
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

    for item in hostnames.strip().split(','):
      hostname = item.strip()
      if hostname:
        self.state.StoreContainer(containers.Host(hostname=hostname))
    self.state.DedupeContainers(containers.Host)

    self.use_raw_filesystem_access = use_raw_filesystem_access
    if max_file_size:
      self.max_file_size = max_file_size

  def Process(self, container: containers.Host) -> None:
    """Collects artifacts from a host with GRR.

    Raises:
      DFTimewolfError: if no artifacts specified nor resolved by platform.
    """
    for client in self._FindClients([container.hostname]):
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
          self.logger.info(
              'Collecting default artifacts for {0:s}: {1:s}'.format(
                  system_type, ', '.join(default_artifacts)))
          artifact_list.extend(default_artifacts)

      if self.extra_artifacts:
        self.logger.info(
            'Throwing in an extra {0!s}'.format(self.extra_artifacts))
        artifact_list.extend(self.extra_artifacts)
        artifact_list = list(set(artifact_list))

      if not artifact_list:
        return

      if client.data.os_info.system.lower() == 'windows':
        self.logger.info('Switching to raw filesystem access for Windows.')
        self.use_raw_filesystem_access = True

      flow_args = flows_pb2.ArtifactCollectorFlowArgs(
          artifact_list=artifact_list,
          use_raw_filesystem_access=self.use_raw_filesystem_access,
          ignore_interpolation_errors=True,
          apply_parsers=False,
          max_file_size=self.max_file_size)
      flow_id = self._LaunchFlow(client, 'ArtifactCollectorFlow', flow_args)
      if not flow_id:
        msg = 'Flow could not be launched on {0:s}.'.format(client.client_id)
        msg += '\nArtifactCollectorFlow args: {0!s}'.format(flow_args)
        self.ModuleError(msg, critical=True)
      self._AwaitFlow(client, flow_id)
      collected_flow_data = self._DownloadFiles(client, flow_id)

      if collected_flow_data:
        self.PublishMessage(f'{flow_id}: Downloaded: {collected_flow_data}')
        cont = containers.File(
            name=client.data.os_info.fqdn.lower(),
            path=collected_flow_data
        )
        self.state.StoreContainer(cont)

  def PreProcess(self) -> None:
    """Not implemented."""

  def PostProcess(self) -> None:
    """Not implemented."""

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    """This module operates on Host containers."""
    return containers.Host


class GRRFileCollector(GRRFlow):
  """File collector for GRR flows.

  Attributes:
    files (list[str]): file paths.
    hosts (list[containers.Host]): Hosts to collect artifacts from.
    use_raw_filesystem_access (bool): True if GRR should use raw disk access to
        collect files.
    action (FileFinderAction): Enum denoting action to take.
  """
  _ACTIONS = {'download': flows_pb2.FileFinderAction.DOWNLOAD,
              'hash': flows_pb2.FileFinderAction.HASH,
              'stat': flows_pb2.FileFinderAction.STAT,
             }

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    super(GRRFileCollector, self).__init__(state, name=name, critical=critical)
    self._clients = []  # type: List[Client]
    self.files = []  # type: List[str]
    self.hosts = []  # type: List[containers.Host]
    self.use_raw_filesystem_access = False
    self.action = None
    self.max_file_size = 5*1024*1024*1024  # 5 GB

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            hostnames: str,
            files: str,
            use_raw_filesystem_access: bool,
            reason: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            max_file_size: str,
            approvers: Optional[str]=None,
            verify: bool=True,
            skip_offline_clients: bool=False,
            action: str='download') -> None:
    """Initializes a GRR file collector.

    Args:
      hostnames (str): comma-separated hostnames to launch the flow on.
      files (str): comma-separated file paths.
      use_raw_filesystem_access (bool): True if GRR should use raw disk access
          to collect files.
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      max_file_size (str): Maximum file size to collect (in bytes).
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

    for item in hostnames.strip().split(','):
      hostname = item.strip()
      if hostname:
        self.state.StoreContainer(containers.Host(hostname=hostname))
    self.state.DedupeContainers(containers.Host)

    self.use_raw_filesystem_access = use_raw_filesystem_access

    if action.lower() in self._ACTIONS:
      self.action = self._ACTIONS[action.lower()]
    if self.action is None:
      self.ModuleError("Invalid action {0!s}".format(action),
                       critical=True)
    if max_file_size:
      self.max_file_size = int(max_file_size)

  def Process(self, container: containers.Host) -> None:
    """Collects files from a host with GRR.

    Raises:
      DFTimewolfError: if no files specified.
    """
    for client in self._FindClients([container.hostname]):
      flow_action = flows_pb2.FileFinderAction(
        action_type=self.action,
        download=flows_pb2.FileFinderDownloadActionOptions(
            max_size=self.max_file_size
        ))

      path_type = jobs_pb2.PathSpec.OS
      # Default to NTFS pathspec to get Windows system-protected files.
      if client.data.os_info.system.lower() == 'windows':
        path_type = jobs_pb2.PathSpec.NTFS

      flow_args = flows_pb2.FileFinderArgs(
          paths=self.files,
          pathtype=path_type,
          action=flow_action)
      flow_id = self._LaunchFlow(client, 'FileFinder', flow_args)
      self._AwaitFlow(client, flow_id)
      collected_flow_data = self._DownloadFiles(client, flow_id)
      if collected_flow_data:
        self.PublishMessage(f'{flow_id}: Downloaded: {collected_flow_data}')
        cont = containers.File(
            name=client.data.os_info.fqdn.lower(),
            path=collected_flow_data
        )
        self.state.StoreContainer(cont)

  def PreProcess(self) -> None:
    """Check that we're actually doing something, and it's not a no-op."""
    for file_container in self.state.GetContainers(
        container_class=containers.FSPath):
      self.files.append(file_container.path)

    if not self.files:
      message = 'Would fetch 0 files - bailing out instead.'
      self.logger.critical(message)
      raise DFTimewolfError(message, critical=False)
    self.logger.info('Filefinder to collect {0:d} items on each host'.format(
        len(self.files)))

  def PostProcess(self) -> None:
    """Check if we're skipping any offline clients."""
    self._CheckSkippedFlows()

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    """This module works on host containers."""
    return containers.Host


class GRROsqueryCollector(GRRFlow):
  """Osquery collector for GRR flows.

  Attributes:
    directory (str): the directory in which to export results.
    timeout_millis (int): the number of milliseconds before osquery timeouts.
    ignore_stderr_errors (bool): ignore stderr errors from osquery.
  """

  DEFAULT_OSQUERY_TIMEOUT_MILLIS = 300000

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    super(GRROsqueryCollector, self).__init__(
        state, name=name, critical=critical)
    self.directory = ""
    self.timeout_millis = self.DEFAULT_OSQUERY_TIMEOUT_MILLIS
    self.ignore_stderr_errors = False

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            hostnames: str,
            reason: str,
            timeout_millis: int,
            ignore_stderr_errors: bool,
            directory: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            approvers: str,
            verify: bool,
            skip_offline_clients: bool) -> None:
    """Initializes a GRR artifact collector.

    Args:
      hostnames (str): comma-separated hostnames to launch the flow on.
      reason (str): justification for GRR access.
      timeout_millis (int): Osquery timeout in milliseconds
      ignore_stderr_errors (bool): Ignore osquery stderr errors
      directory (str): the directory in which to export results.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      approvers (str): list of GRR approval recipients.
      verify (bool): True to indicate GRR server's x509 certificate
          should be verified.
      skip_offline_clients (bool): Whether to wait for flows
          to complete on clients that have been offline for more than an hour.
    """
    super(GRROsqueryCollector, self).SetUp(
        reason, grr_server_url, grr_username, grr_password, approvers=approvers,
        verify=verify, skip_offline_clients=skip_offline_clients)

    if directory and os.path.isdir(directory):
      self.ModuleError('Output directory already exists.', critical=True)

    self.directory = directory

    hosts = set(hostname.strip() for hostname in hostnames.strip().split(','))

    if not hosts:
      self.ModuleError('No hostnames found.', critical=True)

    for hostname in hosts:
      self.state.StoreContainer(containers.Host(hostname=hostname))
    self.state.DedupeContainers(containers.Host)

    self.timeout_millis = timeout_millis
    self.ignore_stderr_errors = ignore_stderr_errors

  def _DownloadResults(self,
                       client: Client,
                       flow_id: str) -> List[pd.DataFrame]:
    """Download osquery results.

    Args:
      client (Client): the GRR Client.
      flow_id (str): the Osquery flow ID to download results from.

    Returns:
      List[pd.DataFrame]: the Osquery results.
    """
    flow = client.Flow(flow_id)
    list_results = list(flow.ListResults())

    if not list_results:
      self.logger.info(f'No rows returned for flow ID {str(flow)}')
      return list_results

    results = []
    for result in list_results:
      payload = result.payload
      if not isinstance(payload, osquery_flows.OsqueryResult):
        self.logger.error(f'Incorrect results format from flow ID {flow}')
        continue

      headers = [column.name for column in payload.table.header.columns]
      data = []
      for row in payload.table.rows:
        data.append(row.values)
      data_frame = pd.DataFrame.from_records(data, columns=headers)
      results.append(data_frame)
    return results

  def Process(self, container: containers.Host) -> None:
    """Collect osquery results from a host with GRR.

    Raises:
      DFTimewolfError: if no artifacts specified nor resolved by platform.
    """
    for client in self._FindClients([container.hostname]):
      osquery_containers = self.state.GetContainers(containers.OsqueryQuery)

      for osquery_container in osquery_containers:
        hunt_args = osquery_flows.OsqueryFlowArgs(
            query=osquery_container.query,
            timeout_millis=self.timeout_millis,
            ignore_stderr_errors=self.ignore_stderr_errors)

        try:
          flow_id = self._LaunchFlow(client, 'OsqueryFlow', hunt_args)
          self._AwaitFlow(client, flow_id)
        except DFTimewolfError as error:
          self.ModuleError(
              f'Error raised while launching/awaiting flow: {error.message}')
          continue

        name = osquery_container.name
        description = osquery_container.description
        query=osquery_container.query
        hostname=container.hostname
        flow_identifier=flow_id
        client_identifier=client.client_id

        results = self._DownloadResults(client, flow_id)
        if not results:
          results_container = containers.OsqueryResult(
              name=name,
              description=description,
              query=query,
              hostname=hostname,
              data_frame=pd.DataFrame(),
              flow_identifier=flow_identifier,
              client_identifier=client_identifier)
          self.state.StoreContainer(results_container)
          continue

        for data_frame in results:
          self.logger.info(
              f'{str(flow_id)} ({container.hostname}): {len(data_frame)} rows '
              'collected')

          dataframe_container = containers.OsqueryResult(
              name=name,
              description=description,
              query=query,
              hostname=hostname,
              data_frame=data_frame,
              flow_identifier=flow_identifier,
              client_identifier=client_identifier)

          self.state.StoreContainer(dataframe_container)

  def PreProcess(self) -> None:
    """Not implemented."""

  def PostProcess(self) -> None:
    """When a directory is specified, get the flow results and save them
       to the directory as CSV files.  A CSV named MANIFEST.csv contains
       details about each flow result.
    """
    if not self.directory:
      return

    if not os.path.isdir(self.directory):
      os.makedirs(self.directory)

    manifest_file_path = os.path.join(self.directory, 'MANIFEST.csv')

    self.logger.info(
        f'Saving osquery flow results to {manifest_file_path}')

    with open(manifest_file_path, mode='w') as manifest_fd:
      manifest_fd.write('"Flow ID","Hostname","GRR Client Id","Osquery"\n')

      for container in self.state.GetContainers(containers.OsqueryResult):
        if not container.query:
          self.logger.error('Query attribute in container is empty.')
          continue
        hostname = container.hostname
        client_id = container.client_identifier
        flow_id = container.client_identifier
        query = container.query

        output_file_path = os.path.join(
            self.directory, '.'.join(
                str(val) for val in (hostname, flow_id, 'csv')))

        with open(output_file_path, mode='w') as fd:
          container.data_frame.to_csv(fd)

        self.logger.info(f'Saved {output_file_path}.')

        manifest_fd.write(f'"{flow_id}","{hostname}","{client_id}","{query}"\n')

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    """This module operates on Host containers."""
    return containers.Host


class GRRFlowCollector(GRRFlow):
  """Flow collector.

  Attributes:
    client_id (str): GRR identifier of the client.
    flow_id (str): GRR identifier of the flow to retrieve.
    host (containers.Host): Target of GRR collection.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    super(GRRFlowCollector, self).__init__(state, name=name, critical=critical)
    self.client_id = str()
    self.flow_id = str()
    self.host: containers.Host

  # pylint: disable=arguments-differ, arguments-renamed
  def SetUp(self,
            hostnames: str,
            flow_ids: str,
            reason: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            approvers: Optional[str]=None,
            verify: bool=True,
            skip_offline_clients: bool=False) -> None:
    """Initializes a GRR flow collector.

    Args:
      hostnames (str): Hostnames to gather the flows from.
      flow_ids (str): GRR identifier of the flows to retrieve.
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

    flows = flow_ids.strip().split(',')
    found_flows = []

    # For each host specified, list their flows
    for item in hostnames.strip().split(','):
      host = item.strip()
      if host:
        client = self._GetClientBySelector(host)
        client_flows = [f.flow_id for f in client.ListFlows()]
        # If the client has a requested flow, queue it up (via the state)
        for f in flows:
          if f in client_flows:
            self.state.StoreContainer(containers.GrrFlow(host, f))
            found_flows.append(f)
    self.state.DedupeContainers(containers.GrrFlow)

    missing_flows = sorted([f for f in flows if f not in found_flows])
    if missing_flows:
      self.logger.warning('The following flows were not found: '
          f'{", ".join(missing_flows)}')
      self.logger.warning('Did you specify a child flow instead of a parent?')

  def Process(self, container: containers.GrrFlow) -> None:
    """Downloads the results of a GRR collection flow.

    Raises:
      DFTimewolfError: if no files specified
    """
    # TODO (tomchop): Change the host attribute into something more appropriate
    # like 'selectors', and the corresponding recipes.
    client = self._GetClientBySelector(container.hostname)
    self._AwaitFlow(client, container.flow_id)
    self._CheckSkippedFlows()
    collected_flow_data = self._DownloadFiles(client, container.flow_id)
    if collected_flow_data:
      self.PublishMessage(
          f'{container.flow_id}: Downloaded: {collected_flow_data}')
      cont = containers.File(
          name=client.data.os_info.fqdn.lower(),
          path=collected_flow_data
      )
      self.state.StoreContainer(cont)
    else:
      self.logger.warning('No flow data collected for '
          f'{container.hostname}:{container.flow_id}')

  def PreProcess(self) -> None:
    """Check that we're actually about to collect anything."""
    if len(self.state.GetContainers(self.GetThreadOnContainerType())) == 0:
      self.ModuleError('No flows found for collection.', critical=True)

  def PostProcess(self) -> None:
    # TODO(ramoj) check if this should be per client in process
    """Check if we're skipping any offline clients."""
    self._CheckSkippedFlows()

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    """This module works on GrrFlow containers."""
    return containers.GrrFlow


class GRRTimelineCollector(GRRFlow):
  """Timeline collector for GRR flows.

  Attributes:
    root_path (bytes): root path.
    hosts (list[containers.Host]): Hosts to collect artifacts from.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    super(GRRTimelineCollector, self).__init__(
        state, name=name, critical=critical)
    self._clients = []  # type: List[Client]
    self.root_path = bytes()
    self.hosts = []  # type: List[containers.Host]
    self._timeline_format = 0

  # We're overriding the behavior of GRRFlow's SetUp function to include new
  # parameters.
  # pylint: disable=arguments-differ,too-many-arguments, arguments-renamed
  def SetUp(self,
            hostnames: str,
            root_path: str,
            reason: str,
            timeline_format: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            approvers: Optional[str]=None,
            verify: bool=True,
            skip_offline_clients: bool=False) -> None:
    """Initializes a GRR timeline collector.
    Args:
      hostnames (str): comma-separated hostnames to launch the flow on.
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

    if root_path:
      self.root_path = root_path.strip().encode()

    for item in hostnames.strip().split(','):
      hostname = item.strip()
      if hostname:
        self.state.StoreContainer(containers.Host(hostname=hostname))
    self.state.DedupeContainers(containers.Host)

    self._timeline_format = int(timeline_format)
    if self._timeline_format not in [1, 2]:
      self.ModuleError('Timeline format must be 1 (BODY) or 2 (RAW).',
                       critical=True)

  def Process(self, container: containers.Host) -> None:
    """Collects a timeline from a host with GRR.

    Raises:
      DFTimewolfError: if no files specified.
    """
    for client in self._FindClients([container.hostname]):
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
        self.PublishMessage(f'{flow_id}: Downloaded: {collected_flow_data}')
        cont = containers.File(
            name=client.data.os_info.fqdn.lower(),
            path=collected_flow_data
        )
        self.state.StoreContainer(cont)

  def _DownloadTimeline(self, client: Client, flow_id: str) -> Optional[str]:
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
      ntfs_inodes = client.data.os_info.system.lower() == 'windows'
      timeline = flow.GetCollectedTimelineBody(
          timestamp_subsecond_precision=True,
          inode_ntfs_file_reference_format=ntfs_inodes,
          backslash_escape=True)
    else:
      timeline = flow.GetCollectedTimeline(self._timeline_format)
    timeline.WriteToFile(output_file_path)

    return output_file_path

  def PreProcess(self) -> None:
    """Not implemented."""

  def PostProcess(self) -> None:
    """Check if we're skipping any offline clients."""
    self._CheckSkippedFlows()

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    """This module works on host containers."""
    return containers.Host


modules_manager.ModulesManager.RegisterModules([
    GRRArtifactCollector,
    GRRFileCollector,
    GRRFlowCollector,
    GRROsqueryCollector,
    GRRTimelineCollector])
