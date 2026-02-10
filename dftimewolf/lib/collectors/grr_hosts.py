# -*- coding: utf-8 -*-
"""Definition of modules for collecting data from GRR hosts."""

import datetime
import os
import pathlib
import re
import stat
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple, Type, Callable

import pandas as pd
from grr_api_client import errors as grr_errors
from grr_api_client import flow, utils
from grr_api_client.client import Client
from grr_response_proto import flows_pb2, jobs_pb2, timeline_pb2
from grr_response_proto import osquery_pb2 as osquery_flows

from dftimewolf.lib import module
from dftimewolf.lib.collectors.grr_base import GRRBaseModule
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.errors import DFTimewolfError
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import cache
from dftimewolf.lib import telemetry
from dftimewolf.lib.containers import manager as container_manager


class GRRError(Exception):
  """Errors raised and handled within the GRR DFTW classes."""


GRR_THREAD_POOL_SIZE = 10 # Arbitrary

# TODO: GRRFlow should be extended by classes that actually implement
# the Process() method.
# pylint: disable=abstract-method
class GRRFlow(GRRBaseModule, module.ThreadAwareModule):
  """Launches and collects GRR flows.

  Modules that use GRR flows or interact with hosts should extend this class.
  """
  _CHECK_FLOW_INTERVAL_SEC = 10
  _MAX_OFFLINE_TIME_SEC = 3600  # One hour
  _LARGE_FILE_SIZE_THRESHOLD = 1 * 1024 * 1024 * 1024  # 1 GB
  _MISSING_FILE_MESSAGE = ('%s was found on the client but not collected, '
                           'probably due to file size: (%d)')

  _CLIENT_ID_REGEX = re.compile(r'^c\.[0-9a-f]{16}$', re.IGNORECASE)

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initializes a GRR flow module.

    Args:
      name: The modules runtime name.
      container_manager_: A common container manager object.
      cache_: A common DFTWCache object.
      telemetry_: A common telemetry collector object.
      publish_message_callback: A callback to send modules messages to.
    """
    module.ThreadAwareModule.__init__(
        self,
        name=name,
        cache_=cache_,
        container_manager_=container_manager_,
        telemetry_=telemetry_,
        publish_message_callback=publish_message_callback)
    GRRBaseModule.__init__(self)
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
    last_seen_datetime = datetime.datetime.fromtimestamp(
        timestamp / 1000000, datetime.timezone.utc)
    # 30 days before now()
    month_ago = (datetime.datetime.now(datetime.timezone.utc) -
                 datetime.timedelta(days=30))
    return last_seen_datetime > month_ago

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
      search_result: utils.ItemsIterator[Client]) -> List[Tuple[int, Client]]:
    result = []
    selector = selector.lower()
    for client in search_result:
      fqdn_match = selector in client.data.os_info.fqdn.lower()
      client_id_match = selector in client.data.client_id.lower()
      usernames = [user.username for user in client.data.knowledge_base.users]
      username_match = selector in usernames and len(usernames) == 1
      if fqdn_match or client_id_match or username_match:
        result.append((client.data.last_seen_at, client))
    return result

  # TODO: change object to more specific GRR type information.
  def _GetClientBySelector(
      self, selector: str, discard_inactive: bool = True) -> Client:
    """Searches GRR by selector and get the latest active client.

    Args:
      selector (str): selector to search for. This can be a hostname or GRR
          client ID.
      discard_inactive: Whether to filter out clients that are considered
          inactive (one month since last check-in).

    Returns:
      object: GRR API Client object

    Raises:
      DFTimewolfError: if no client ID found for selector.
    """
    # Search for the selector in GRR
    self.logger.debug(f"Searching for client: {selector:s}")
    try:
      search_result = self.grr_api.SearchClients(selector)
    except grr_errors.UnknownError as exception:
      self.ModuleError('Could not search for host {0:s}: {1!s}'.format(
          selector, exception
      ), critical=True)

    clients = self._FilterSelectionCriteria(selector, search_result)

    if not clients:
      self.ModuleError(f'Could not get client for {selector:s}', critical=True)

    if discard_inactive:
      clients = self._FilterActiveClients(clients)
      if not clients:
        self.ModuleError(
              f'{len(clients)} inactive/old clients were found '
              f'for selector: "{selector}", none of them '
              'has been active in the last 30 days.', critical=True)

    if len(clients) > 1:
      self.ModuleError(
            f'Multiple hosts ({len(clients)}) with the same '
            f'selector: "{selector}" have been found.\n'
            'Please use e.g. client ID instead of the hostname.',
            critical=True)

    last_seen, client = clients[0]
    # Remove microseconds and create datetime object
    last_seen_datetime = datetime.datetime.fromtimestamp(
        last_seen / 1000000, datetime.timezone.utc)
    # Timedelta between now and when the client was last seen, in minutes.
    # First, count total seconds. This will return a float.
    last_seen_seconds = (datetime.datetime.now(datetime.timezone.utc) -
                         last_seen_datetime).total_seconds()
    last_seen_minutes = int(round(last_seen_seconds / 60))

    self.logger.info(f'Found client: {client.client_id:s}')
    self.logger.debug(
      "Client last seen: {0:s} ({1:d} minutes ago)".format(
        last_seen_datetime.strftime("%Y-%m-%dT%H:%M:%S+0000"), last_seen_minutes
      )
    )

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

  def VerifyClientAccess(self, client: Client) -> None:
    """Verifies and requests access to a GRR client.

    This call will block until the approval is granted.

    Args:
      client: GRR client object to verify access to.
    """
    client_fqdn = client.data.knowledge_base.fqdn

    try:
      client.VerifyAccess()
      self.logger.info(f"Access to {client_fqdn} granted")
      return
    except grr_errors.AccessForbiddenError:
      self.logger.warning(f"No access to {client_fqdn}, requesting...")

    approval = client.CreateApproval(
      reason=self.reason,
      notified_users=self.approvers,
      expiration_duration_days=30,
    )

    approval_url = (
      f"{self.grr_url}/v2/clients/{approval.client_id}"
      f"/approvals/{approval.approval_id}/users/{approval.username}"
    )
    self.PublishMessage(f"Approval URL: {approval_url}")
    approval.WaitUntilValid()
    self.logger.info(f"Access to {client_fqdn} granted")

  # TODO: change object to more specific GRR type information.
  def _LaunchFlow(self, client: Client, name: str, args: str) -> str:
    """Creates the specified flow.

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
    try:
      grr_flow = self._WrapGRRRequestWithApproval(
        client,
        client.CreateFlow,
        self.logger,
        self.LogTelemetry,
        name=name,
        args=args,
      )
    except DFTimewolfError as exception:
      self.ModuleError(exception.message, critical=exception.critical)
    if not grr_flow:
      return ''

    flow_id = str(grr_flow.flow_id)  # pytype: disable=attribute-error
    self.PublishMessage(f"{flow_id}: Flow scheduled")

    return flow_id

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

  def _AwaitFlow(self, client: Client, flow_id: str) -> None:
    """Waits for a specific GRR flow to complete.

    Args:
      client (object): GRR Client object in which to await the flow.
      flow_id (str): GRR identifier of the flow to await.

    Raises:
      DFTimewolfError: If a Flow error was encountered.
    """
    self.logger.info(f"{flow_id:s}: Waiting to finish")
    if self.skip_offline_clients:
      self.logger.debug("Client will be skipped if offline.")

    while True:
      try:
        status = client.Flow(flow_id).Get().data
      except grr_errors.UnknownError:
        msg = (
          f"Unknown error retrieving flow {flow_id} for host "
          f"{client.data.os_info.fqdn.lower()}"
        )
        self.ModuleError(msg, critical=True)

      if status.state == flows_pb2.FlowContext.ERROR:
        # TODO(jbn): If one artifact fails, what happens? Test.
        message = status.context.backtrace
        if "ArtifactNotRegisteredError" in status.context.backtrace:
          message = status.context.backtrace.split("\n")[-2]
        self.ModuleError(
          f"{flow_id:s}: FAILED! Message from GRR:\n{message:s}",
          critical=True,
        )

      if status.state == 4:  # Flow crashed, no enum in flows_pb2
        self.ModuleError(f"{flow_id:s}: Crashed", critical=False)
        break

      if status.state == flows_pb2.FlowContext.TERMINATED:
        self.logger.info(f"{flow_id:s}: Complete")
        break

      time.sleep(self._CHECK_FLOW_INTERVAL_SEC)
      if not self.skip_offline_clients:
        continue

      client_last_seen = datetime.datetime.fromtimestamp(
        client.data.last_seen_at / 1000000, datetime.timezone.utc
      )
      now = datetime.datetime.now(datetime.timezone.utc)
      if (now - client_last_seen).total_seconds() > self._MAX_OFFLINE_TIME_SEC:
        self.logger.warning(
          "Client {0:s} has been offline for more than {1:.1f} minutes"
          ", skipping...".format(
            client.client_id, self._MAX_OFFLINE_TIME_SEC / 60
          )
        )
        self._skipped_flows.append((client.client_id, flow_id))
        break

  def _DownloadBlobs(
      self,
      client: Client,
      payloads: List[
          jobs_pb2.StatEntry
          | jobs_pb2.PathSpec
          | flows_pb2.FileFinderResult
          | flows_pb2.CollectFilesByKnownPathResult
          | flows_pb2.CollectBrowserHistoryResult
      ],
      flow_output_dir: str,
  ) -> None:
    """Download individual collected files from GRR to the local filesystem.

    Args:
      client: GRR Client object to download blobs from.
      payloads: List of pathspecs to download blobs from.
      flow_output_dir: Directory to store the downloaded files.

    Raises:
      RuntimeError: if the file collection is not supported.
    """
    stats: jobs_pb2.StatEntry = None
    pathspec: jobs_pb2.PathSpec = None
    size: int = 0
    vfspath: str = ''

    for payload in payloads:
      match type(payload):
        case jobs_pb2.StatEntry:
          if not hasattr(payload, 'pathspec'):
            raise RuntimeError('Unsupported file collection attempted')
          pathspec = payload.pathspec
          size = payload.st_size
          if stat.S_ISDIR(payload.st_mode):
            continue
        case (
            jobs_pb2.PathSpec
            | flows_pb2.FileFinderResult
            | flows_pb2.CollectFilesByKnownPathResult
            | flows_pb2.CollectBrowserHistoryResult
            | flows_pb2.CollectMultipleFilesResult
        ):
          if hasattr(payload, 'stat'):
            stats = payload.stat
          elif hasattr(payload, 'stat_entry'):
            stats = payload.stat_entry
          size = stats.st_size
          if stat.S_ISDIR(stats.st_mode):
            continue
        case _:
          raise RuntimeError('Unsupported file collection attempted')

      if stats:
        pathspec = stats.pathspec
      if pathspec.nested_path.pathtype == jobs_pb2.PathSpec.NTFS:
        vfspath = f'fs/ntfs{pathspec.path}{pathspec.nested_path.path}'
      else:
        vfspath = re.sub('^([a-zA-Z]:)?/(.*)$', 'fs/os/\\1/\\2', pathspec.path)

      filename = os.path.basename(vfspath)
      base_dir = os.path.join(flow_output_dir, os.path.dirname(vfspath))
      os.makedirs(base_dir, exist_ok=True)

      f = client.File(vfspath)
      self.logger.debug(f'Downloading blob {filename} from {vfspath}')
      try:
        path = os.path.join(base_dir, filename)
        if size:
          with open(path, 'wb') as out:
            self.logger.debug(f"Downloading {filename} to: {path}")
            f.GetBlob().WriteToStream(out)
        else:
          pathlib.Path(path).touch()
      except grr_errors.ResourceNotFoundError as e:
        self.logger.warning(
            f'Failed to download blob {filename} from {vfspath}: {e}'
        )

  def _DownloadTimeline(
    self,
    client: Client,
    grr_flow: Client.Flow,
    flow_output_dir: str,
  ) -> str:
    """Downloads a bodyfile timeline from a GRR client.

    Args:
      client: GRR Client object to download the timeline from.
      grr_flow: GRR TimelineFlow object to download the timeline from.
      flow_output_dir: Directory to store the downloaded timeline.

    Returns:
      Full path to the downloaded timeline.
    """
    final_bodyfile_path = os.path.join(
      flow_output_dir, f"{grr_flow.flow_id}_timeline.body"
    )
    ntfs_inodes = client.data.os_info.system.lower() == "windows"
    timeline = grr_flow.GetCollectedTimelineBody(
      timestamp_subsecond_precision=True,
      inode_ntfs_file_reference_format=ntfs_inodes,
      backslash_escape=True,
    )
    timeline.WriteToFile(final_bodyfile_path)
    return final_bodyfile_path

  def _DownloadOsquery(
      self,
      client: Client,
      flow_id: str,
      flow_output_dir: str
  ) -> Optional[str]:
    """Download osquery results as a CSV file.

    Args:
      client: the GRR Client.
      flow_id: the Osquery flow ID to download results from.
      flow_output_dir: the directory to store the downloaded timeline.

    Returns:
      str: the path to the CSV file or None if there are no results.
    """
    grr_flow = client.Flow(flow_id)
    list_results = list(grr_flow.ListResults())

    if not list_results:
      self.logger.warning(f"No results returned for flow ID {flow_id}")
      return None

    results = []
    for result in list_results:
      payload = result.payload
      if isinstance(payload, osquery_flows.OsqueryCollectedFile):
        # We don't do anything with any collected files for now as we are just
        # interested in the osquery results.
        self.logger.info(
            f'Skipping collected file - {payload.stat_entry.pathspec}.')
        continue
      if not isinstance(payload, osquery_flows.OsqueryResult):
        self.logger.error(f'Incorrect results format from flow ID {flow_id}')
        continue

      headers = [column.name for column in payload.table.header.columns]
      data = []
      for row in payload.table.rows:
        data.append(row.values)
      data_frame = pd.DataFrame.from_records(data, columns=headers)
      results.append(data_frame)

    fqdn = client.data.os_info.fqdn.lower()
    output_file_path = os.path.join(
        flow_output_dir,
        '.'.join(str(val) for val in (fqdn, flow_id, 'csv')))
    with open(output_file_path, mode='w') as fd:
      merged_data_frame = pd.concat(results)
      merged_data_frame.to_csv(fd)

    return output_file_path

  def _DownloadFiles(self, client: Client, flow_id: str) -> Optional[str]:
    """Download files/results from the specified flow.

    Args:
      client: GRR Client object to which to download flow data from.
      flow_id: GRR identifier of the flow.

    Returns:
      str: path containing the downloaded files.
    """
    flow_handle = client.Flow(flow_id).Get()

    fqdn = client.data.os_info.fqdn.lower()
    flow_output_dir = os.path.join(self.output_path, fqdn, flow_id)
    os.makedirs(flow_output_dir, exist_ok=True)

    flow_name = flow_handle.data.name
    if flow_name == 'TimelineFlow':
      self.logger.info('Downloading timeline from GRR')
      self._DownloadTimeline(client, flow_handle, flow_output_dir)
      return flow_output_dir

    if flow_name == 'OsqueryFlow':
      self.logger.info('Downloading osquery results from GRR')
      self._DownloadOsquery(client, flow_id, flow_output_dir)
      return flow_output_dir

    try:
      missing = self._CheckForMissingFiles(flow_handle)
      if missing:
        message = '\n'.join([self._MISSING_FILE_MESSAGE % (path, size)
                             for path, size in missing])
        self.logger.warning(f'\n{message}\n')
    except GRRError:
      pass

    payloads = []
    for r in flow_handle.ListResults():
      payloads.append(r.payload)
    self.logger.info('Downloading data blobs from GRR')
    self._DownloadBlobs(client, payloads, flow_output_dir)

    return flow_output_dir

  def _CheckForMissingFiles(
      self, flow_handle: flow.Flow) -> list[tuple[str, int]]:
    """Check a ClientFileFinder result list for files that weren't collected.

    Args:
      flow_handle: A flow to check for missing files.

    Returns:
      A list of tuples of:
        A file where collection was skipped or failed
        The file size in bytes
    """
    results = list(flow_handle.ListResults())
    if not results:
      raise DFTimewolfError(
          f'No FileFinder results for {flow_handle.flow_id}')
    if flow_handle.data.name != 'ClientFileFinder':
      raise GRRError()
    missing: list[tuple[str, int]] = []
    for result in results:
      payload = flows_pb2.FileFinderResult()
      result.data.payload.Unpack(payload)
      if not payload.HasField('transferred_file'):
        pathspec = payload.stat_entry.pathspec
        if pathspec.mount_point and pathspec.nested_path.path:
          pathname = pathspec.mount_point + pathspec.nested_path.path
        else:
          pathname = pathspec.path
        missing.append((pathname, payload.stat_entry.st_size))
    return missing

  def GetThreadPoolSize(self) -> int:
    """Thread pool size."""
    return GRR_THREAD_POOL_SIZE


class GRRYaraScanner(GRRFlow):
  """GRR Yara scanner.

  Launches YaraProcessScans against one or multiple hosts, stores a pandas
  DataFrame containing results.
  """

  # can be overridden for internal modules to group on.
  GROUPING_KEY = 'grouping_key'

  REPORT_TEXT = """
GRR Yara scan found {0:d} matches on `{1:s}`.

Scanned rules:

* {2:s}

Flow ID: {3:s}
  """

  YARA_MODULES = {
    "hash.": "import \"hash\"",
    "pe.": "import \"pe\"",
    "elf.": "import \"elf\"",
    "math.": "import \"math\"",
  }

  FLOW_NAME = 'YaraProcessScan'

  # pylint: disable=arguments-differ
  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)
    self.process_ignorelist_regex = ''
    self.cmdline_ignorelist_regex = ''
    self.rule_text = ''
    self.rule_count = 0
    self._grouping = ''
    self.rule_names = ''
    self.dump_process_on_match = False

  # pylint: disable=too-many-arguments
  def SetUp(self,
            reason: str,
            hostnames: str,
            process_ignorelist: str,
            cmdline_ignorelist: str,
            dump_process_on_match: bool,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            approvers: Optional[str] = None,
            verify: bool = True,
            skip_offline_clients: bool = False
            ) -> None:  # pytype: disable=signature-mismatch

    super().SetUp(
      reason, grr_server_url, grr_username, grr_password,
      approvers=approvers, verify=verify,
      skip_offline_clients=skip_offline_clients)

    for hostname in hostnames.strip().split(','):
      hostname = hostname.strip()
      if hostname:
        self.StoreContainer(containers.Host(hostname=hostname))

    if process_ignorelist and cmdline_ignorelist:
      raise DFTimewolfError(
          'Only one of process_ignorelist or cmd_ignorelist can be specified')

    if process_ignorelist:
      process_joined = ""
      if isinstance(process_ignorelist, list):
        process_joined = "|".join(process_ignorelist)
      elif isinstance(process_ignorelist, str):
        process_joined = process_ignorelist

      self.process_ignorelist_regex = r"(?i)^(?!.*(" + process_joined + r")).*"

    if cmdline_ignorelist:
      cmdline_joined = ""
      if isinstance(cmdline_ignorelist, list):
        cmdline_joined = "|".join(cmdline_ignorelist)
      elif isinstance(cmdline_ignorelist, str):
        cmdline_joined = cmdline_ignorelist

      self.cmdline_ignorelist_regex = r"(?i)^(?!.*(" + cmdline_joined + r")).*"

    if self.process_ignorelist_regex:
      try:
        re.compile(self.process_ignorelist_regex)
      except re.error as exception:
        self.ModuleError(
          f'Invalid regex for process_ignorelist: {exception}', critical=True)

    if self.cmdline_ignorelist_regex:
      try:
        re.compile(self.cmdline_ignorelist_regex)
      except re.error as exception:
        self.ModuleError(
          f'Invalid regex for cmdline_ignorelist: {exception}', critical=True)

    self.dump_process_on_match = dump_process_on_match

  def PreProcess(self) -> None:
    """Concatenates Yara rules into one stacked rule.

    This is so we only launch one GRR Flow per host, instead of N Flows for N
    rules that were stored upstream.
    """
    yara_containers = self.GetContainers(containers.YaraRule)
    if not yara_containers:
      self.logger.warning('No Yara rules found.')
      return

    selected_headers = set()
    for rule in yara_containers:
      for prefix, header in self.YARA_MODULES.items():
        condition = rule.rule_text.split("condition:")[1]
        if prefix in condition:
          selected_headers.add(header)

    concatenated_rules = '\n\n'.join([r.rule_text for r in yara_containers])
    final_rule_text = '\n'.join(selected_headers) + '\n\n' + concatenated_rules
    self.rule_text = final_rule_text
    self.rule_count = len(yara_containers)
    self.rule_names = ', '.join([r.name for r in yara_containers])
    self._grouping = f'# GRR Yara Scan - {datetime.datetime.now()}'

  def Process(self, container: containers.Host
              ) -> None:  # pytype: disable=signature-mismatch
    if not self.rule_count:
      return

    self.logger.debug(
      f"Running {self.rule_count} Yara sigs against {container.hostname}"
    )

    hits = 0
    flows = []
    for client in self._FindClients([container.hostname]):
      grr_hostname = client.data.os_info.fqdn
      flow_args = flows_pb2.YaraProcessScanRequest(
        yara_signature=self.rule_text,
        ignore_grr_process=True,
        process_regex=self.process_ignorelist_regex,
        cmdline_regex=self.cmdline_ignorelist_regex,
        skip_mapped_files=False,
        dump_process_on_match=self.dump_process_on_match,
      )

      flow_id = self._LaunchFlow(client, self.FLOW_NAME, flow_args)
      self.logger.info(
        f'Launched flow {flow_id} on {client.client_id} ({grr_hostname})')

      grr_flow = client.Flow(flow_id)
      self._AwaitFlow(client, flow_id)

      grr_flow = grr_flow.Get()
      results = list(grr_flow.ListResults())
      yara_hits_df = self._YaraHitsToDataFrame(client, results)

      flows.append((
        grr_flow.client_id,
        grr_flow.flow_id,
        not yara_hits_df.empty))
      if yara_hits_df.empty:
        self.logger.info(
          f"{flow_id}: No Yara hits on {grr_hostname}" f" ({client.client_id})"
        )
        continue

      self.logger.info(f'{flow_id}: found Yara hits on {grr_hostname}'
                          f' ({client.client_id})')
      dataframe = containers.DataFrame(
        data_frame=yara_hits_df,
        description=(f'List of processes in {grr_hostname} ({client.client_id})'
                     ' with Yara hits.'),
        name=f'Yara matches on {grr_hostname} ({client.client_id})',
        source='GRRYaraCollector')
      dataframe.SetMetadata(self.GROUPING_KEY, self._grouping)
      self.StoreContainer(dataframe)
      hits += 1

    flow_string = ', '.join([f'`{c}:{f}` (hits: {h})' for c, f, h in flows])
    flow_string = flow_string.replace('hits: True', 'hits: **True**')
    report_text = self.REPORT_TEXT.format(
        hits,
        container.hostname,
        '\n* '.join(self.rule_names.split(', ')),
        flow_string)
    report = containers.Report(
        'GRRYaraScan',  # actually used as report title
        report_text,
        text_format='markdown',
        metadata={self.GROUPING_KEY: self._grouping})

    self.StoreContainer(report)

  def PostProcess(self) -> None:
    """Not implemented."""

  def _YaraHitsToDataFrame(
    self,
    client: Client,
    results: List[flow.FlowResult]) -> pd.DataFrame:
    """Converts results of a GRR YaraProcessScan Flow to a pandas DataFrame.

    Args:
      client: The GRR client object that had matches.
      results: The FlowResult object obtained by calling ListResults on the
          GRR Flow object.

    Returns:
      A pandas DataFrame containing client / process / signature match
      information.
    """

    entries = []
    for r in results:
      if not isinstance(r.payload, flows_pb2.YaraProcessScanMatch):
        continue
      process = r.payload.process
      for match in r.payload.match:
        string_matches = set(sm.string_id for sm in match.string_matches)
        entries.append({
            'grr_client': client.client_id,
            'grr_fqdn': client.data.os_info.fqdn,
            'pid': process.pid,
            'username': process.username,
            'rule_name': match.rule_name,
            'string_matches': sorted(list(string_matches)),
            'cmdline': ' '.join(process.cmdline),
            'process': process.exe,
            'cwd': process.cwd,
        })
    return pd.DataFrame(entries)

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    """This module operates on Host containers."""
    return containers.Host


class GRRArtifactCollector(GRRFlow):
  """Artifact collector for GRR flows.

  Attributes:
    artifacts (list[str]): artifact definition names.
    extra_artifacts (list[str]): extra artifact definition names.
    hosts (list[containers.Host]): Hosts to collect artifacts from.
    use_raw_filesystem_access (bool): True if GRR should use raw disk access to
        collect file system artifacts.
  """

  DEFAULT_ARTIFACTS_LINUX = [
      # keep-sorted start
      'LinuxAuditLogs',
      'LinuxAuthLogs',
      'LinuxCronLogs',
      'LinuxWtmp',
      'ShellHistoryFile',
      'ZeitgeistDatabase',
      # keep-sorted end
  ]

  DEFAULT_ARTIFACTS_DARWIN = [
      # keep-sorted start
      'BashShellHistoryFile',
      'MacOSAppleSetupDoneFile',
      'MacOSAppleSystemLogFile',
      'MacOSAuditLogFile',
      'MacOSInstallationHistoryPlistFile',
      'MacOSInstallationLogFile',
      'MacOSLaunchAgentsPlistFile',
      'MacOSLaunchDaemonsPlistFile',
      'MacOSLogFile',
      'MacOSQuarantineEventsSQLiteDatabaseFile',
      'MacOSRecentItemsPlistFile',
      'MacOSSystemLogFile',
      'MacOSUserApplicationLogFile',
      # keep-sorted end
  ]

  DEFAULT_ARTIFACTS_WINDOWS = [
      # keep-sorted start
      'WindowsAppCompatCache',
      'WindowsEventLogs',
      'WindowsPrefetchFiles',
      'WindowsScheduledTasks',
      'WindowsSearchDatabase',
      'WindowsSuperFetchFiles',
      'WindowsSystemRegistryFiles',
      'WindowsUserRegistryFiles',
      'WindowsXMLEventLogTerminalServices'
      # keep-sorted end
  ]

  artifact_registry = {
      'Linux': DEFAULT_ARTIFACTS_LINUX,
      'Darwin': DEFAULT_ARTIFACTS_DARWIN,
      'Windows': DEFAULT_ARTIFACTS_WINDOWS
  }

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)
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
            max_file_size: Optional[str],
            approvers: Optional[str]=None,
            verify: bool=True,
            skip_offline_clients: bool=False
            ) -> None:  # pytype: disable=signature-mismatch
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
      max_file_size (Optional[str]): Maximum file size to collect (in bytes).
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
        self.StoreContainer(containers.Host(hostname=hostname))

    self.use_raw_filesystem_access = use_raw_filesystem_access
    if max_file_size and isinstance(max_file_size, str):
      self.max_file_size = int(max_file_size)

  def Process(self, container: containers.Host
              ) -> None:  # pytype: disable=signature-mismatch
    """Collects artifacts from a host with GRR.

    Raises:
      DFTimewolfError: if no artifacts specified nor resolved by platform.
    """

    if not self.artifacts:
      artifact_containers = self.GetContainers(containers.GRRArtifact)
      self.logger.debug(
        "GRR artifact containers were found: {0!s}".format(artifact_containers)
      )
      if artifact_containers:
        self.artifacts = [artifact.name for artifact in artifact_containers]

    for client in self._FindClients([container.hostname]):
      system_type = client.data.os_info.system
      self.logger.debug(f"System type: {system_type:s}")

      # If the list is supplied by the user via a flag, honor that.
      artifact_list = []
      if self.artifacts:
        self.logger.debug(f"Artifacts to be collected: {self.artifacts!s}")
        artifact_list = self.artifacts
      else:
        default_artifacts = self.artifact_registry.get(system_type, None)
        if default_artifacts:
          self.logger.debug(
            "Collecting default artifacts for {0:s}: {1:s}".format(
              system_type, ", ".join(default_artifacts)
            )
          )
          artifact_list.extend(default_artifacts)

      if self.extra_artifacts:
        self.logger.debug(f"Throwing in an extra {self.extra_artifacts!s}")
        artifact_list.extend(self.extra_artifacts)
        artifact_list = list(set(artifact_list))

      if not artifact_list:
        return

      flow_args = flows_pb2.ArtifactCollectorFlowArgs(
        artifact_list=artifact_list,
        use_raw_filesystem_access=self.use_raw_filesystem_access,
        ignore_interpolation_errors=True,
        max_file_size=self.max_file_size,
        implementation_type=jobs_pb2.PathSpec.ImplementationType.DIRECT,
      )
      flow_id = self._LaunchFlow(client, 'ArtifactCollectorFlow', flow_args)
      if not flow_id:
        msg = f'Flow could not be launched on {client.client_id:s}.'
        msg += f'\nArtifactCollectorFlow args: {flow_args!s}'
        self.ModuleError(msg, critical=True)
      self._AwaitFlow(client, flow_id)

      collected_flow_data = self._DownloadFiles(client, flow_id)

      if collected_flow_data:
        self.logger.info(f'{flow_id}: Downloaded: {collected_flow_data}')
        cont = containers.File(
            name=client.data.os_info.fqdn.lower(),
            path=collected_flow_data
        )
        cont.metadata['SOURCE_MACHINE'] = client.client_id
        self.StoreContainer(cont)

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
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)
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
            action: str='download'
            ) -> None:  # pytype: disable=signature-mismatch
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
        self.StoreContainer(containers.Host(hostname=hostname))

    self.use_raw_filesystem_access = use_raw_filesystem_access

    if action.lower() in self._ACTIONS:
      self.action = self._ACTIONS[action.lower()]
    if self.action is None:
      self.ModuleError(f"Invalid action {action!s}",
                       critical=True)
    if max_file_size and isinstance(max_file_size, str):
      self.max_file_size = int(max_file_size)

  def Process(self, container: containers.Host
              ) -> None:  # pytype: disable=signature-mismatch
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
        self.logger.info(f'{flow_id}: Downloaded: {collected_flow_data}')
        cont = containers.File(
            name=client.data.os_info.fqdn.lower(),
            path=collected_flow_data
        )
        cont.metadata['SOURCE_MACHINE'] = client.client_id
        self.StoreContainer(cont)

  def PreProcess(self) -> None:
    """Check that we're actually doing something, and it's not a no-op."""
    for file_container in self.GetContainers(
        container_class=containers.FSPath):
      self.files.append(file_container.path)

    if not self.files:
      message = 'Would fetch 0 files - bailing out instead.'
      self.logger.critical(message)
      raise DFTimewolfError(message, critical=False)
    self.logger.debug(
      f"Filefinder to collect {len(self.files):d} items on each host"
    )

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
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)
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
            skip_offline_clients: bool
            ) -> None:  # pytype: disable=signature-mismatch
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
      self.StoreContainer(containers.Host(hostname=hostname))

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
    grr_flow = client.Flow(flow_id)
    list_results = list(grr_flow.ListResults())

    if not list_results:
      self.logger.warning(f"No rows returned for flow ID {str(grr_flow)}")
      return list_results

    results = []
    for result in list_results:
      payload = result.payload
      if isinstance(payload, osquery_flows.OsqueryCollectedFile):
        # We don't do anything with any collected files for now as we are just
        # interested in the osquery results.
        self.logger.info(f'File collected - {payload.stat_entry.pathspec}.')
        continue
      if not isinstance(payload, osquery_flows.OsqueryResult):
        self.logger.error(f'Incorrect results format from flow ID {grr_flow}')
        continue

      headers = [column.name for column in payload.table.header.columns]
      data = []
      for row in payload.table.rows:
        data.append(row.values)
      data_frame = pd.DataFrame.from_records(data, columns=headers)
      results.append(data_frame)
    return results

  def _ProcessQuery(
      self,
      hostname: str,
      client: Client,
      osquery_container: containers.OsqueryQuery
  ) -> None:
    """Processes an osquery flow on a GRR client.

    Args:
      hostname: the GRR client hostname.
      client: the GRR Client.
      osquery_container: the OSQuery.
    """
    query = osquery_container.query
    if not query.strip().endswith(';'):
      query += ';'

    flow_args = osquery_flows.OsqueryFlowArgs()
    flow_args.query = query
    flow_args.timeout_millis = self.timeout_millis
    flow_args.ignore_stderr_errors = self.ignore_stderr_errors
    flow_args.configuration_content = osquery_container.configuration_content
    flow_args.configuration_path = osquery_container.configuration_path
    flow_args.file_collection_columns.extend(
        osquery_container.file_collection_columns)

    try:
      flow_id = self._LaunchFlow(client, 'OsqueryFlow', flow_args)
      self._AwaitFlow(client, flow_id)
    except DFTimewolfError as error:
      self.ModuleError(
        f"Error raised while launching/awaiting flow: {error.message}"
      )
      return

    name = osquery_container.name
    description = osquery_container.description
    flow_identifier = flow_id
    client_identifier = client.client_id

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
      self.StoreContainer(results_container)
      return

    merged_results = pd.concat(results)
    self.logger.info(
        f'{str(flow_id)} ({hostname}): {len(merged_results)} rows collected')

    dataframe_container = containers.OsqueryResult(
        name=name,
        description=description,
        query=query,
        hostname=hostname,
        data_frame=merged_results,
        flow_identifier=flow_identifier,
        client_identifier=client_identifier)

    self.StoreContainer(dataframe_container)

  def Process(self, container: containers.Host
              ) -> None:  # pytype: disable=signature-mismatch
    """Collect osquery results from a host with GRR.

    Raises:
      DFTimewolfError: if no artifacts specified nor resolved by platform.
    """
    client = self._GetClientBySelector(container.hostname)

    osquery_containers = self.GetContainers(containers.OsqueryQuery)

    host_osquery_futures = []
    with ThreadPoolExecutor(self.GetQueryThreadPoolSize()) as executor:
      for osquery_container in osquery_containers:
        host_osquery_future = executor.submit(
          self._ProcessQuery, container.hostname, client, osquery_container)
        host_osquery_futures.append(host_osquery_future)

    for host_osquery_future in host_osquery_futures:
      if host_osquery_future.exception():
        self.logger.error(
            f'Error with osquery flow {str(host_osquery_future.exception())}')

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

    self.logger.info(f"Saving osquery flow results to {manifest_file_path}")

    with open(manifest_file_path, mode='w') as manifest_fd:
      manifest_fd.write('"Flow ID","Hostname","GRR Client Id","Osquery"\n')

      for container in self.GetContainers(containers.OsqueryResult):
        if not container.query:
          self.logger.error('Query attribute in container is empty.')
          continue
        hostname = container.hostname
        client_id = container.client_identifier
        flow_id = container.flow_identifier
        query = container.query

        output_file_path = os.path.join(
            self.directory, '.'.join(
                str(val) for val in (hostname, flow_id, 'csv')))

        with open(output_file_path, mode='w') as fd:
          container.data_frame.to_csv(fd)

        self.logger.info(f"Saved OSQuery dataframe to {output_file_path}.")

        manifest_fd.write(f'"{flow_id}","{hostname}","{client_id}","{query}"\n')

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    """This module operates on Host containers."""
    return containers.Host

  def GetQueryThreadPoolSize(self) -> int:
    """Get the number of osquery threads."""
    return 4  # Arbitrary


class GRRFlowCollector(GRRFlow):
  """Flow collector.

  Attributes:
    client_id (str): GRR identifier of the client.
    flow_id (str): GRR identifier of the flow to retrieve.
    host (containers.Host): Target of GRR collection.
  """

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)

    self.client_id = str()
    self.flow_id = str()
    self.host: containers.Host

  # pylint: disable=arguments-differ, arguments-renamed, missing-raises-doc
  def SetUp(self,
            hostnames: str,
            flow_ids: str,
            reason: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            approvers: Optional[str]=None,
            verify: bool=True,
            skip_offline_clients: bool=False
            ) -> None:  # pytype: disable=signature-mismatch
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
    for item in hostnames.strip().split(','):
      host = item.strip()
      if host:
        client = self._GetClientBySelector(host)
        for flow_id in flows:
          self.logger.info(
                f'Verifying client access for {client.client_id}...'
            )
          try:
            self.VerifyClientAccess(client)
            client.Flow(flow_id).Get()
            self.StoreContainer(containers.GrrFlow(host, flow_id))
          except Exception as exception:  # pylint: disable=broad-except
            if all((s in str(exception) for s in [client.client_id, flow_id])):
              self.logger.warning(
                  f'Flow {flow_id} not found in {client.client_id}')
            else:
              raise exception

  def Process(self, container: containers.GrrFlow
              ) -> None:  # pytype: disable=signature-mismatch
    """Downloads the results of a GRR collection flow.

    Raises:
      DFTimewolfError: if no files specified
    """
    # We don't need clients to be online to grab the flows.
    client = self._GetClientBySelector(
        container.hostname, discard_inactive=False)
    self._AwaitFlow(client, container.flow_id)
    self._CheckSkippedFlows()
    collected_flow_data = self._DownloadFiles(client, container.flow_id)
    if collected_flow_data:
      self.logger.info(
          f'{container.flow_id}: Downloaded: {collected_flow_data}')
      cont = containers.File(
          name=client.data.os_info.fqdn.lower(),
          path=collected_flow_data
      )
      cont.metadata['SOURCE_MACHINE'] = client.client_id
      self.StoreContainer(cont)
    else:
      self.logger.warning('No flow data collected for '
          f'{container.hostname}:{container.flow_id}')

  def PreProcess(self) -> None:
    """Check that we're actually about to collect anything."""
    if len(self.GetContainers(self.GetThreadOnContainerType())) == 0:
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
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)

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
            skip_offline_clients: bool=False
            ) -> None:  # pytype: disable=signature-mismatch
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
        self.StoreContainer(containers.Host(hostname=hostname))

    self._timeline_format = int(timeline_format)
    if self._timeline_format not in [1, 2]:
      self.ModuleError('Timeline format must be 1 (BODY) or 2 (RAW).',
                       critical=True)

  def Process(self, container: containers.Host
              ) -> None:  # pytype: disable=signature-mismatch
    """Collects a timeline from a host with GRR.

    Raises:
      DFTimewolfError: if no files specified.
    """
    for client in self._FindClients([container.hostname]):
      root_path = self.root_path
      if not root_path:
        return
      self.logger.debug(
        f'Timeline to start from "{root_path.decode():s}" items'
      )

      timeline_args = timeline_pb2.TimelineArgs(root=root_path,)
      flow_id = self._LaunchFlow(client, 'TimelineFlow', timeline_args)
      self._AwaitFlow(client, flow_id)
      collected_timeline = self._DownloadTimeline(
        client, client.Flow(flow_id), self.output_path
      )
      self.logger.info(f"{flow_id}: Downloaded: {collected_timeline}")
      cont = containers.File(
        name=client.data.os_info.fqdn.lower(), path=collected_timeline
      )
      cont.metadata['SOURCE_MACHINE'] = client.client_id
      self.StoreContainer(cont)

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
    GRRTimelineCollector,
    GRRYaraScanner])
