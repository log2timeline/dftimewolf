# -*- coding: utf-8 -*-
"""Timewolf artifact collectors.

Timewolf artifact collectors are responsible for collecting artifacts.
"""

import datetime
import os
import re
import tempfile
import threading
import time
import zipfile

from grr.gui.api_client import api as grr_api
from grr.gui.api_client import errors as grr_errors
from dftimewolf.lib import utils as timewolf_utils
from grr.proto import flows_pb2


class BaseArtifactCollector(threading.Thread):
  """Base class for artifact collectors.

  Attributes:
    console_out: Console output helper
  """

  def __init__(self, verbose):
    """Initialize the base artifact collector object.

    Args:
      verbose (Optional[bool]): whether verbose output is desired.
    """
    super(BaseArtifactCollector, self).__init__()
    self.console_out = timewolf_utils.TimewolfConsoleOutput(
        sender=self.__class__.__name__, verbose=verbose)
    self.results = []

  def run(self):
    self.results = self.Collect()

  def Collect(self):
    """Collect artifacts.

    Returns:
      list(tuple): containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.
    """
    raise NotImplementedError

  @property
  def collection_name(self):
    """Name for the collection of artifacts."""
    raise NotImplementedError


class FilesystemCollector(BaseArtifactCollector):
  """Collect artifacts from the local filesystem.

  Attributes:
    output_path: Path to where to store collected artifacts.
    cname: Name for the collection of collected artifacts.
  """

  def __init__(self, path, name=None, verbose=False):
    """Initializes a filesystem collector.

    Args:
      path (str): path to the files to collect.
      name (Optional[str]): name of the collection.
      verbose (Optional[bool]): whether verbose output is desired.
    """
    super(FilesystemCollector, self).__init__(verbose=verbose)
    self.cname = name
    self.output_path = path

  def Collect(self):
    """Collect the files.

    Returns:
      list[tuple]: containing:
        str: the name provided for the collection.
        str: path to the files for collection.
    """
    self.console_out.VerboseOut(u'Artifact path: {0:s}'.format(
        self.output_path))
    return [(self.cname, self.output_path)]

  @property
  def collection_name(self):
    """Name for the collection of collected artifacts.

    Returns:
      str: name of the artifact collection
    """
    if not self.cname:
      self.cname = os.path.basename(self.output_path.rstrip(u'/'))
    self.console_out.VerboseOut(u'Artifact collection name: {0:s}'.format(
        self.cname))
    return self.cname


class GRRHuntCollector(BaseArtifactCollector):
  """Collect hunt results with GRR.

  Attributes:
    output_path: Path to where to store collected artifacts
    grr_api: GRR HTTP API client
    artifacts: List of GRR artifacts names
    use_tsk: Toggle for use_tsk flag on GRR flow
    reason: Justification for GRR access
    approvers: list of GRR approval recipients
  """
  _CHECK_APPROVAL_INTERVAL_SEC = 10

  def __init__(self,
               hunt_id,
               artifacts,
               use_tsk,
               reason,
               grr_server_url,
               username,
               password,
               approvers=None,
               verbose=False):
    """ Initializes a GRR hunt results collector.

    Args:
      hunt_id (str): ID of GRR hunt to retrieve artifacts from
      artifacts (str): comma-separated list of ForensicArtifacts
      use_tsk (bool): toggle for use_tsk flag on GRR flows and hunts
      reason (str): justification for GRR access
      grr_server_url (str): GRR server url
      username (str): GRR server username
      password (str): GRR server password
      approvers (Optional[str]): comma-separated list of GRR approval recipients
      verbose (Optional[bool]): toggle for verbose output
    """
    super(GRRHuntCollector, self).__init__(verbose=verbose)
    self.output_path = tempfile.mkdtemp()
    self.grr_api = grr_api.InitHttp(
        api_endpoint=grr_server_url, auth=(username, password))
    self.artifacts = artifacts
    self.use_tsk = use_tsk
    self.approvers = approvers
    self.reason = reason
    if not hunt_id:
      self._NewHunt()
    else:
      self.hunt_id = hunt_id
      self._hunt = self.grr_api.Hunt(hunt_id).Get()

  def _NewHunt(self):
    """Create new GRR hunt."""
    if self.artifacts:
      artifact_list = self.artifacts.split(u',')
    if not artifact_list:
      raise RuntimeError(u'No artifacts to collect')

    name = u'ArtifactCollectorFlow'
    args = flows_pb2.ArtifactCollectorFlowArgs(
        artifact_list=artifact_list,
        use_tsk=self.use_tsk,
        ignore_interpolation_errors=True,
        apply_parsers=False,)
    runner_args = self.grr_api.Types.HuntRunnerArgs(description=self.reason)
    self._hunt = self.grr_api.CreateHunt(
        flow_name=name, flow_args=args, hunt_runner_args=runner_args)
    self.hunt_id = self._hunt.hunt_id
    self.console_out.VerboseOut(u'Hunt {0:s} created'.format(self.hunt_id))

    try:
      self._hunt.Start()
    except grr_errors.AccessForbiddenError:
      self.console_out.VerboseOut(u'No valid hunt approval found')
      if not self.approvers:
        raise ValueError(u'GRR hunt needs approval but no approvers specified '
                         u'(hint: use --approvers)')
      self.console_out.VerboseOut(
          u'Hunt {0:s}: approval request sent to: {1:s} (reason: {2:s})'.format(
              self.hunt_id, self.approvers, self.reason))
      self.console_out.VerboseOut(
          u'Hunt {0:s}: Waiting for approval (this can take a while..)'.format(
              self.hunt_id))
      # Send a request for approval and wait until there is a valid one
      # available in GRR.
      self._hunt.CreateApproval(
          reason=self.reason, notified_users=self.approvers)
      while True:
        try:
          self._hunt.Start()
          self.console_out.VerboseOut(u'Hunt approval is valid.')
          break
        except grr_errors.AccessForbiddenError:
          time.sleep(self._CHECK_APPROVAL_INTERVAL_SEC)

  def Status(self):
    """Print status of hunt."""
    status = self.grr_api.Hunt(self.hunt_id).Get().data
    self.console_out.StdOut(
        u'Status of hunt {0:s}\nTotal clients: {1:d}\nCompleted clients: '
        u'{2:d}\nOutstanding clients: {3:d}\n'.
        format(self.hunt_id, status.all_clients_count,
               status.completed_clients_count, status.remaining_clients_count))

  def Collect(self):
    """Download current set of files in results.

    Returns:
      list(tuple): containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.
    """
    if not os.path.isdir(self.output_path):
      os.makedirs(self.output_path)

    output_file_path = os.path.join(self.output_path, u'.'.join(
        (self.hunt_id, u'zip')))

    if os.path.exists(output_file_path):
      print u'{0:s} already exists: Skipping'.format(output_file_path)
      return None

    try:
      self._hunt.GetFilesArchive().WriteToFile(output_file_path)
    except grr_errors.AccessForbiddenError:
      self.console_out.VerboseOut(u'No valid hunt approval found')
      if not self.approvers:
        raise ValueError(u'GRR hunt needs approval but no approvers specified '
                         u'(hint: use --approvers)')
      self.console_out.VerboseOut(
          u'Hunt {0:s}: approval request sent to: {1:s} (reason: {2:s})'.format(
              self.hunt_id, self.approvers, self.reason))
      self.console_out.VerboseOut(
          u'Hunt {0:s}: Waiting for approval (this can take a while..)'.format(
              self.hunt_id))
      # Send a request for approval and wait until there is a valid one
      # available in GRR.
      self._hunt.CreateApproval(
          reason=self.reason, notified_users=self.approvers)
      while True:
        try:
          hunt_archive = self._hunt.GetFilesArchive()
          hunt_archive.WriteToFile(output_file_path)
          self.console_out.VerboseOut(
              u'Hunt {0:s}: Downloaded results to {1:s}'.format(
                  self.hunt_id, output_file_path))
          break
        except grr_errors.AccessForbiddenError:
          time.sleep(self._CHECK_APPROVAL_INTERVAL_SEC)

    # Extract items from archive by host for processing
    collection_paths = []
    with zipfile.ZipFile(output_file_path) as archive:
      items = archive.infolist()
      base = items[0].filename.split(u'/')[0]
      for f in items:
        client_id = f.filename.split(u'/')[1]
        if client_id.startswith(u'C.'):
          client = self.grr_api.Client(client_id).Get()
          client_name = client.data.os_info.fqdn
          client_directory = os.path.join(self.output_path, client_id)
          if not os.path.isdir(client_directory):
            os.makedirs(client_directory)
            collection_paths.append((client_name, client_directory))
          real_file_path = os.path.join(base, u'hashes',
                                        os.path.basename(archive.read(f)))
          try:
            archive.extract(real_file_path, client_directory)
            os.rename(
                os.path.join(client_directory, real_file_path),
                os.path.join(client_directory, os.path.basename(f.filename)))
          except KeyError, e:
            self.console_out.StdErr(u'Extraction error: {0:s}'.format(e))

    os.remove(output_file_path)

    return collection_paths

  @property
  def collection_name(self):
    """Name for the collection of collected artifacts."""
    collection_name = u'{0:s}: {1:s}'.format(
        self.hunt_id, self._hunt.data.hunt_runner_args.description)
    self.console_out.VerboseOut(u'Artifact collection name: {0:s}'.format(
        collection_name))
    return collection_name


class GRRArtifactCollector(BaseArtifactCollector):
  """Collect artifacts with GRR.

  Attributes:
    output_path: Path to where to store collected artifacts
    grr_api: GRR HTTP API client
    artifacts: List of GRR artifacts names
    host: Target of GRR collection
    use_tsk: Toggle for use_tsk flag on GRR flow
    reason: Justification for GRR access
    approvers: list of GRR approval recipients
    client_id: GRR client ID
    client: Dictionary with information about a GRR client
  """
  _CHECK_APPROVAL_INTERVAL_SEC = 10
  _CHECK_FLOW_INTERVAL_SEC = 10
  _DEFAULT_ARTIFACTS_LINUX = [
      u'LinuxAuditLogs', u'LinuxAuthLogs', u'LinuxCronLogs', u'LinuxWtmp',
      u'AllUsersShellHistory', u'ZeitgeistDatabase'
  ]

  _DEFAULT_ARTIFACTS_DARWIN = [
      u'OSXAppleSystemLogs', u'OSXAuditLogs', u'OSXBashHistory',
      u'OSXInstallationHistory', u'OSXInstallationLog', u'OSXInstallationTime',
      u'OSXLaunchAgents', u'OSXLaunchDaemons', u'OSXMiscLogs',
      u'OSXRecentItems', u'OSXSystemLogs', u'OSXUserApplicationLogs',
      u'OSXQuarantineEvents'
  ]

  _DEFAULT_ARTIFACTS_WINDOWS = [
      u'AppCompatCache', u'EventLogs', u'TerminalServicesEventLogEvtx',
      u'PrefetchFiles', u'SuperFetchFiles', u'WindowsSearchDatabase',
      u'ScheduledTasks', u'WindowsSystemRegistryFiles',
      u'WindowsUserRegistryFiles'
  ]

  def __init__(self,
               hostname,
               reason,
               grr_server_url,
               username,
               password,
               artifacts=None,
               use_tsk=False,
               approvers=None,
               verbose=False):
    """Initializes a GRR artifact collector.

    Args:
      hostname (str): hostname of machine to extract artifacts from
      reason (str): justification for GRR access
      grr_server_url (str): GRR server url
      username (str): GRR server username
      password (str): GRR server password
      artifacts (str): comma-separated list of ForensicArtifacts
      use_tsk (Optional[bool]): toggle for use_tsk flag on GRR flow
      approvers (Optional[str]): comma-separated list of GRR approval recipients
      verbose (Optional[bool]): toggle for verbose output
    """
    super(GRRArtifactCollector, self).__init__(verbose=verbose)
    self.output_path = tempfile.mkdtemp()
    self.grr_api = grr_api.InitHttp(
        api_endpoint=grr_server_url, auth=(username, password))
    self.artifacts = artifacts
    self.host = hostname
    self.use_tsk = use_tsk
    self.reason = reason
    self.approvers = approvers
    self._client_id = self._GetClientId(hostname)
    self._client = None

  def _GetClientId(self, hostname):
    """Search GRR by hostname and get the latest active client.

    Args:
      hostname (str): hostname to search for.

    Returns:
      str: ID of most recently active client.
    """
    client_id_pattern = re.compile(r'^c\.[0-9a-f]{16}$', re.IGNORECASE)
    if client_id_pattern.match(hostname):
      return hostname

    # Search for the hostname in GRR
    self.console_out.VerboseOut(u'Searching for client: {0:s}'.format(hostname))
    search_result = self.grr_api.SearchClients(hostname)

    result = {}
    for client in search_result:
      client_id = client.client_id
      client_fqdn = client.data.os_info.fqdn
      client_last_seen_at = client.data.last_seen_at
      if hostname.lower() in client_fqdn.lower():
        result[client_id] = client_last_seen_at

    if not result:
      raise RuntimeError(u'Could not get client_id for {0:s}'.format(hostname))

    active_client_id = sorted(result, key=result.get, reverse=True)[0]
    last_seen_timestamp = result[active_client_id]
    # Remove microseconds and create datetime object
    last_seen_datetime = datetime.datetime.utcfromtimestamp(
        last_seen_timestamp / 1000000)
    # Timedelta between now and when the client was last seen, in minutes.
    # First, count total seconds. This will return a float.
    last_seen_seconds = (
        datetime.datetime.utcnow() - last_seen_datetime).total_seconds()
    last_seen_minutes = int(round(last_seen_seconds)) / 60

    self.console_out.VerboseOut(u'Found active _client: {0:s}'.format(
        active_client_id))
    self.console_out.VerboseOut(
        u'Client last seen: {0:s} ({1:d} minutes ago)'.format(
            last_seen_datetime.strftime(u'%Y-%m-%dT%H:%M:%S+0000'),
            last_seen_minutes))

    return active_client_id

  def _GetClient(self, client_id, reason, approvers):
    """Get GRR client dictionary and make sure valid approvals exist.

    Args:
      client_id (str): GRR client ID
      reason (str): justification for GRR access
      approvers (str): comma-separated list of GRR approval recipients

    Returns:
      GRR API Client object

    Raises:
      ValueError: if no approvals exist and no approvers are specified
    """
    client = self.grr_api.Client(client_id)
    self.console_out.VerboseOut(u'Checking for client approval')
    try:
      client.ListFlows()
    except grr_errors.AccessForbiddenError:
      self.console_out.VerboseOut(u'No valid client approval found')
      if not approvers:
        raise ValueError(
            u'GRR client needs approval but no approvers specified '
            u'(hint: use --approvers)')
      self.console_out.VerboseOut(
          u'Client approval request sent to: {0:s} (reason: {1:s})'.format(
              approvers, reason))
      self.console_out.VerboseOut(
          u'Waiting for approval (this can take a while...)')
      # Send a request for approval and wait until there is a valid one
      # available in GRR.
      client.CreateApproval(reason=reason, notified_users=approvers)
      while True:
        try:
          client.ListFlows()
          break
        except grr_errors.AccessForbiddenError:
          time.sleep(self._CHECK_APPROVAL_INTERVAL_SEC)

    self.console_out.VerboseOut(u'Client approval is valid')
    return client.Get()

  def Collect(self):
    """Collect the artifacts.

    Returns:
      list(tuple): containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.
    """
    # Create a list of artifacts to collect.
    artifact_registry = {
        u'Linux': self._DEFAULT_ARTIFACTS_LINUX,
        u'Darwin': self._DEFAULT_ARTIFACTS_DARWIN,
        u'Windows': self._DEFAULT_ARTIFACTS_WINDOWS
    }
    self._client = self._GetClient(self._client_id, self.reason, self.approvers)
    system_type = self._client.data.os_info.system
    self.console_out.VerboseOut(u'System type: {0:s}'.format(system_type))
    # If the list is supplied by the user via a flag, honor that.
    if self.artifacts:
      artifact_list = self.artifacts.split(u',')
    else:
      artifact_list = artifact_registry.get(system_type, None)
    if not artifact_list:
      raise RuntimeError(u'No artifacts to collect')

    name = u'ArtifactCollectorFlow'
    args = flows_pb2.ArtifactCollectorFlowArgs(
        artifact_list=artifact_list,
        use_tsk=self.use_tsk,
        ignore_interpolation_errors=True,
        apply_parsers=False,)

    self.console_out.VerboseOut(u'Artifacts to collect: {0:s}'.format(
        artifact_list))

    # Start the flow and get the flow ID
    flow = self._client.CreateFlow(name=name, args=args)
    flow_id = flow.flow_id
    self.console_out.VerboseOut(u'Flow {0:s}: Scheduled'.format(flow_id))

    # Wait for the flow to finish
    self.console_out.VerboseOut(u'Flow {0:s}: Waiting to finish'.format(
        flow_id))
    while True:
      status = self._client.Flow(flow_id).Get().data
      state = status.state
      if state == flows_pb2.FlowContext.ERROR:
        # TODO(berggren): If one artifact fails, what happens? Test.
        raise RuntimeError(u'Flow {0:s}: FAILED! Backtrace from GRR:\n\n{1:s}'.
                           format(flow_id, status.context.backtrace))
      elif state == flows_pb2.FlowContext.TERMINATED:
        self.console_out.VerboseOut(u'Flow {0:s}: Finished successfully'.format(
            flow_id))
        break
      time.sleep(self._CHECK_FLOW_INTERVAL_SEC)

    # Download the files collected by the flow
    self.console_out.VerboseOut(u'Flow {0:s}: Downloading artifacts'.format(
        flow_id))
    collected_file_path = self._DownloadFiles(flow_id)

    if collected_file_path:
      self.console_out.VerboseOut(u'Flow {0:s}: Downloaded: {1:s}'.format(
          flow_id, collected_file_path))

    return [(self.host, self.output_path)]

  def _DownloadFiles(self, flow_id):
    """Download files from the specified flow.

    Args:
      flow_id (str): GRR flow ID

    Returns:
      str: path of downloaded files
    """
    if not os.path.isdir(self.output_path):
      os.makedirs(self.output_path)

    output_file_path = os.path.join(self.output_path, u'.'.join(
        (flow_id, u'zip')))

    if os.path.exists(output_file_path):
      print u'{0:s} already exists: Skipping'.format(output_file_path)
      return None

    flow = self._client.Flow(flow_id)
    file_archive = flow.GetFilesArchive()
    file_archive.WriteToFile(output_file_path)

    # Unzip archive for processing and remove redundant zip
    with zipfile.ZipFile(output_file_path) as archive:
      archive.extractall(path=self.output_path)
    os.remove(output_file_path)

    return output_file_path

  @property
  def collection_name(self):
    """Name for the collection of collected artifacts."""
    collection_name = self._client.data.os_info.fqdn
    self.console_out.VerboseOut(u'Artifact collection name: {0:s}'.format(
        collection_name))
    return collection_name


def CollectArtifactsHelper(host_list, new_hunt, hunt_status, hunt_id, path_list,
                           artifact_list, use_tsk, reason, approvers, verbose,
                           grr_server_url, username, password):
  """Helper function to collect artifacts based on command line flags passed.

  Args:
      host_list: comma-separated list of hosts to collect artifacts from
      new_hunt (Optional[bool]): toggle for starting new GRR hunt
      hunt_status (Optional[bool]): toggle for getting status of ongoing hunt
      hunt_id (str): ID of GRR hunt to retrieve artifacts from
      path_list (Optional [str]): comma-separated list of local artifact paths
      artifact_list (str): comma-separated list of ForensicArtifacts
      use_tsk (Optional[bool]): toggle for use_tsk flag on GRR flows and hunts
      reason (str): justification for GRR access
      approvers (str): comma-separated list of GRR approval recipients
      verbose (Optional[bool]): toggle for verbose output
      grr_server_url (str): GRR server url
      username (str): GRR server username
      password (str): GRR server password

  Returns:
      list(tuple): containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.

  """
  # Build list of collectors and start collection in parallel
  collectors = []
  for host in host_list:
    collector = GRRArtifactCollector(
        host,
        reason,
        grr_server_url,
        username,
        password,
        artifact_list,
        use_tsk,
        approvers,
        verbose=verbose)
    collector.start()
    collectors.append(collector)

  for path in path_list:
    collector = FilesystemCollector(path, verbose=verbose)
    collector.start()
    collectors.append(collector)

  if new_hunt or hunt_id:
    collector = GRRHuntCollector(
        hunt_id,
        artifact_list,
        use_tsk,
        reason,
        grr_server_url,
        username,
        password,
        approvers,
        verbose=verbose)
    if new_hunt:
      collector.console_out.StdOut(
          u'Hunt started. Run timewolf with --hunt_id {0:s} for results'.format(
              collector.hunt_id))
    elif hunt_status:
      collector.Status()
    else:
      collector.start()
      collectors.append(collector)

  # Wait for all collectors to finish
  for collector in collectors:
    collector.join()

  collector_results = []
  for collector in collectors:
    collector_results += collector.results

  return collector_results
