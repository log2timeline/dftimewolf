# -*- coding: utf-8 -*-
"""Collects artifacts with GRR."""

from __future__ import unicode_literals

import datetime
import os
import re
import syslog
import tempfile
import time
import zipfile

from dftimewolf.lib.collectors.collectors import BaseCollector

from grr_api_client import errors as grr_errors
from grr_api_client import api as grr_api
from grr_api_client.proto.grr.proto import flows_pb2


class GRRHuntCollector(BaseCollector):
  """Base collector for GRR hunt collections.

  Attributes:
    output_path: Path to store collected artifacts.
    grr_api: GRR HTTP API client.
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
    hunt_id: Identifier of the hunt being collected.
  """
  _CHECK_APPROVAL_INTERVAL_SEC = 10

  def __init__(
      self, reason, grr_server_url, grr_auth, approvers=None, verbose=False):
    """Initializes a GRR hunt results collector.

    Args:
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.
    """
    super(GRRHuntCollector, self).__init__(verbose=verbose)
    self._hunt = None
    self.approvers = approvers
    self.grr_api = grr_api.InitHttp(api_endpoint=grr_server_url, auth=grr_auth)
    self.hunt_id = None
    self.output_path = tempfile.mkdtemp()
    self.reason = reason

  def _StartHunt(self, name, args):
    """Create specified hunt.

    Args:
      name: string containing hunt name.
      args: proto (*FlowArgs) for type of hunt, as defined in GRR flow proto.

    Returns:
      str representing hunt ID.

    Raises:
      ValueError: if approval is needed and approvers were not specified.
    """
    runner_args = self.grr_api.types.CreateHuntRunnerArgs()
    runner_args.description = self.reason
    hunt = self.grr_api.CreateHunt(
        flow_name=name, flow_args=args, hunt_runner_args=runner_args)
    hunt_id = hunt.hunt_id
    syslog.syslog('Hunt {0:s}: Created'.format(hunt_id))
    self.console_out.VerboseOut('Hunt {0:s}: Created'.format(hunt_id))

    try:
      hunt.Start()
      return hunt_id

    except grr_errors.AccessForbiddenError:
      syslog.syslog('Hunt {0:s}: No valid hunt approval found'.format(hunt_id))
      self.console_out.VerboseOut('No valid hunt approval found')
      if not self.approvers:
        raise ValueError(
            'GRR hunt needs approval but no approvers specified '
            '(hint: use --approvers)')
      self.console_out.VerboseOut(
          'Hunt {0:s}: approval request sent to: {1:s} (reason: {2:s})'.format(
              hunt_id, self.approvers, self.reason))
      self.console_out.VerboseOut(
          'Hunt {0:s}: Waiting for approval (this can take a while..)'.format(
              hunt_id))
      # Send a request for approval and wait until there is a valid one
      # available in GRR.
      hunt.CreateApproval(reason=self.reason, notified_users=self.approvers)
      syslog.syslog(
          'Hunt {0:s}: Request for hunt approval sent'.format(hunt_id))

      while True:
        try:
          hunt.Start()
          syslog.syslog('Hunt {0:s}: Hunt approval is valid'.format(hunt_id))
          self.console_out.VerboseOut('Hunt approval is valid.')
          return hunt_id
        except grr_errors.AccessForbiddenError:
          time.sleep(self._CHECK_APPROVAL_INTERVAL_SEC)

  def collect(self):
    """Download current set of files in results.

    Returns:
      list: tuples containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.
    Raises:
      ValueError: if approval is needed and approvers were not specified.
    """
    if not os.path.isdir(self.output_path):
      os.makedirs(self.output_path)

    output_file_path = os.path.join(
        self.output_path, '.'.join((self.hunt_id, 'zip')))

    if os.path.exists(output_file_path):
      self.console_out.StdOut(
          '{0:s} already exists: Skipping'.format(output_file_path))
      return None

    try:
      self._hunt.GetFilesArchive().WriteToFile(output_file_path)
      syslog.syslog('Hunt {0:s}: Results downloaded'.format(self.hunt_id))
      self.console_out.VerboseOut(
          'Hunt {0:s}: Downloaded: {1:s}'.format(
              self.hunt_id, output_file_path))
    except grr_errors.AccessForbiddenError:
      syslog.syslog(
          'Hunt {0:s}: No valid hunt approval found'.format(self.hunt_id))
      self.console_out.VerboseOut('No valid hunt approval found')
      if not self.approvers:
        raise ValueError(
            'GRR hunt needs approval but no approvers specified '
            '(hint: use --approvers)')
      self.console_out.VerboseOut(
          'Hunt {0:s}: approval request sent to: {1:s} (reason: {2:s})'.format(
              self.hunt_id, self.approvers, self.reason))
      self.console_out.VerboseOut(
          'Hunt {0:s}: Waiting for approval (this can take a while..)'.format(
              self.hunt_id))
      # Send a request for approval and wait until there is a valid one
      # available in GRR.
      self._hunt.CreateApproval(
          reason=self.reason, notified_users=self.approvers)
      syslog.syslog(
          'Hunt {0:s}: Request for hunt approval sent'.format(self.hunt_id))

      while True:
        try:
          hunt_archive = self._hunt.GetFilesArchive()
          hunt_archive.WriteToFile(output_file_path)
          self.console_out.VerboseOut(
              'Hunt {0:s}: Downloaded results to {1:s}'.format(
                  self.hunt_id, output_file_path))
          syslog.syslog('Hunt {0:s}: Results downloaded'.format(self.hunt_id))
          self.console_out.VerboseOut(
              'Hunt {0:s}: Downloaded: {1:s}'.format(
                  self.hunt_id, output_file_path))
          break
        except grr_errors.AccessForbiddenError:
          time.sleep(self._CHECK_APPROVAL_INTERVAL_SEC)
    return self._ExtractHuntResults(output_file_path)

  def _ExtractHuntResults(self, output_file_path):
    """Open a hunt output archive and extract files.

    Args:
      output_file_path: The path where the hunt archive is downloaded to.

    Returns:
      list: tuples containing:
          str: The name of the client from where the files were downloaded.
          str: The directory where the files were downloaded to.
    """
    # Extract items from archive by host for processing
    collection_paths = []
    with zipfile.ZipFile(output_file_path) as archive:
      items = archive.infolist()
      base = items[0].filename.split('/')[0]
      for f in items:
        client_id = f.filename.split('/')[1]
        if client_id.startswith('C.'):
          client = self.grr_api.Client(client_id).Get()
          client_name = client.data.os_info.fqdn
          client_directory = os.path.join(self.output_path, client_id)
          if not os.path.isdir(client_directory):
            os.makedirs(client_directory)
          collection_paths.append((client_name, client_directory))
          real_file_path = os.path.join(
              base, 'hashes', os.path.basename(archive.read(f)))
          try:
            archive.extract(real_file_path, client_directory)
            os.rename(
                os.path.join(client_directory, real_file_path),
                os.path.join(client_directory, os.path.basename(f.filename)))
          except KeyError as exception:
            self.console_out.StdErr('Extraction error: {0:s}'.format(exception))
            return None

    os.remove(output_file_path)

    return collection_paths

  def PrintStatus(self):
    """Print status of hunt."""
    status = self.grr_api.Hunt(self.hunt_id).Get().data
    self.console_out.StdOut(
        'Status of hunt {0:s}\nTotal clients: {1:d}\nCompleted clients: '
        '{2:d}\nOutstanding clients: {3:d}\n'.format(
            self.hunt_id, status.all_clients_count,
            status.completed_clients_count, status.remaining_clients_count))

  @property
  def collection_name(self):
    """Name for the collection of collected artifacts."""
    collection_name = '{0:s}: {1:s}'.format(
        self.hunt_id, self._hunt.data.hunt_runner_args.description)
    self.console_out.VerboseOut(
        'Artifact collection name: {0:s}'.format(collection_name))
    return collection_name


class GRRHuntArtifactCollector(GRRHuntCollector):
  """Artifact collector for GRR hunts.

  Attributes:
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
    artifacts: comma-separated list of GRR-defined artifacts.
    use_tsk: toggle for use_tsk flag.
  """

  def __init__(
      self,
      reason,
      grr_server_url,
      grr_auth,
      artifacts,
      use_tsk,
      approvers=None,
      verbose=False):
    """Initializes a GRR Hunt artifact collector.

    Args:
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      artifacts: str, comma-separated list of GRR-defined artifacts.
      use_tsk: toggle for use_tsk flag.
      approvers: str, comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.
    """
    super(GRRHuntArtifactCollector, self).__init__(
        reason, grr_server_url, grr_auth, approvers=approvers, verbose=verbose)
    self.artifacts = artifacts
    self.use_tsk = use_tsk
    self.hunt_id = self._NewHunt()
    self._hunt = self.grr_api.Hunt(self.hunt_id).Get()

  def _NewHunt(self):
    """Construct and start new GRR hunt.

    Returns:
      str representing hunt ID.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    artifact_list = self.artifacts.split(',')
    if not artifact_list:
      raise RuntimeError('Artifacts must be specified for artifact collection')

    syslog.syslog('Artifacts to be collected: {0:s}'.format(self.artifacts))
    hunt_name = 'ArtifactCollectorFlow'
    hunt_args = self.grr_api.types.CreateFlowArgs('ArtifactCollectorFlow')
    for artifact in artifact_list:
      hunt_args.artifact_list.append(artifact)
    hunt_args.use_tsk = self.use_tsk
    hunt_args.ignore_interpolation_errors = True
    hunt_args.apply_parsers = False

    return self._StartHunt(hunt_name, hunt_args)

  @staticmethod
  def launch_collector(
      reason, grr_server_url, grr_auth, artifacts, use_tsk, approvers, verbose):
    """Start a file collector Hunt using GRRHuntFileCollector.

    Args:
      reason: Justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      artifacts: Comma-separated list of artifacts to collect.
      use_tsk: toggle for use_tsk flag on GRR flow.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.

    Returns:
      An empty list, since this launches a Hunt and no processors can be
          immediately called.
    """
    hunt = GRRHuntArtifactCollector(
        reason, grr_server_url, grr_auth, artifacts, use_tsk, approvers,
        verbose)
    hunt.console_out.StdOut(
        '\nArtifact hunt {0:s} created successfully!'.format(hunt.hunt_id))
    hunt.console_out.StdOut('Run a GRRHuntDownloader recipe to fetch results.')
    hunt.console_out.StdOut(
        'e.g. $ dftimewolf grr_huntresults_plaso_timesketch {0:s}\n'.format(
            hunt.hunt_id))
    return []


class GRRHuntFileCollector(GRRHuntCollector):
  """File collector for GRR hunts.

  Attributes:
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
    file_list: comma-separated list of file paths.
  """

  def __init__(
      self,
      reason,
      grr_server_url,
      grr_auth,
      file_list,
      approvers=None,
      verbose=False):
    """Initializes a GRR Hunt file collector.

    Args:
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      file_list: comma-separated list of file paths.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.
    """
    super(GRRHuntFileCollector, self).__init__(
        reason, grr_server_url, grr_auth, approvers=approvers, verbose=verbose)
    self.file_list = file_list
    self.hunt_id = self._NewHunt()
    self._hunt = self.grr_api.Hunt(self.hunt_id).Get()

  def _NewHunt(self):
    """Construct and start new GRR hunt.

    Returns:
      str representing hunt ID.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    file_list = self.file_list.split(',')
    if not file_list:
      raise RuntimeError('File must be specified for hunts')

    syslog.syslog('Hunt to collect {0:d} items'.format(len(self.file_list)))
    self.console_out.VerboseOut(
        'Files to be collected: {0:s}'.format(self.file_list))
    hunt_name = 'FileFinder'

    hunt_action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.DOWNLOAD,)
    hunt_args = flows_pb2.FileFinderArgs(
        paths=file_list,
        action=hunt_action,)

    return self._StartHunt(hunt_name, hunt_args)

  @staticmethod
  def launch_collector(
      reason, grr_server_url, grr_auth, file_list, approvers=None,
      verbose=False):
    """Start a file collector Hunt using GRRHuntFileCollector.

    Args:
      reason: Justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      file_list: Comma-separated list of files to download in the Hunt.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.

    Returns:
      An empty list, since this launches a Hunt and no processors can be
          immediately called.
    """
    hunt = GRRHuntFileCollector(
        reason, grr_server_url, grr_auth, file_list, approvers, verbose)
    hunt.console_out.StdOut(
        '\nHunt {0:s} created successfully!'.format(hunt.hunt_id))
    hunt.console_out.StdOut('Run a GRRHuntDownloader recipe to fetch results.')
    hunt.console_out.StdOut(
        'e.g. $ dftimewolf grr_huntresults_plaso_timesketch {0:s}\n'.format(
            hunt.hunt_id))

    return []


class GRRHuntDownloader(GRRHuntCollector):
  """File collector for GRR hunts.

  Attributes:
    reason: justification for GRR access.
    approvers: list of GRR approval recipients.
    hunt_id: ID of GRR hunt to retrieve results from.
  """

  def __init__(
      self,
      reason,
      grr_server_url,
      grr_auth,
      hunt_id,
      approvers=None,
      verbose=False):
    """Initializes a GRR hunt results collector.

    Args:
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      hunt_id: ID of GRR hunt to retrieve results from.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.
    """
    super(GRRHuntDownloader, self).__init__(
        reason, grr_server_url, grr_auth, approvers=approvers, verbose=verbose)
    self.hunt_id = hunt_id
    self._hunt = self.grr_api.Hunt(self.hunt_id).Get()

  @staticmethod
  def launch_collector(
      reason, grr_server_url, grr_auth, hunt_id, approvers=None, verbose=False):
    """Downloads the files found during a given GRR Hunt.

    Args:
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      hunt_id: GRR Hunt id to download files from.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.

    Returns:
      An list containing the started Hunt downloader collector.
    """
    hunt_downloader = GRRHuntDownloader(
        reason, grr_server_url, grr_auth, hunt_id, approvers, verbose)
    hunt_downloader.start()
    return [hunt_downloader]


class GRRHostCollector(BaseCollector):
  """Collect artifacts with GRR.

  Attributes:
    output_path: Path to where to store collected items.
    grr_api: GRR HTTP API client.
    host: Target of GRR collection.
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
  """
  _CHECK_APPROVAL_INTERVAL_SEC = 10
  _CHECK_FLOW_INTERVAL_SEC = 10

  _CLIENT_ID_REGEX = re.compile(r'^c\.[0-9a-f]{16}$', re.IGNORECASE)

  def __init__(
      self,
      hostname,
      reason,
      grr_server_url,
      grr_auth,
      approvers=None,
      verbose=False,
      keepalive=False):
    """Initializes a GRR collector.

    Args:
      hostname: hostname of machine.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.
      keepalive: toggle for scheduling a KeepAlive flow.
    """
    super(GRRHostCollector, self).__init__(verbose=verbose)
    self.output_path = tempfile.mkdtemp()
    self.grr_api = grr_api.InitHttp(api_endpoint=grr_server_url, auth=grr_auth)
    self.host = hostname
    self.reason = reason
    self.approvers = approvers
    self._client_id = self._GetClientId(hostname)
    self._client = None
    self.keepalive = keepalive
    self.flow_id = None

  def collect(self):
    """Collect artifacts.

    Not implemented, as this is an abstract class.
    """
    raise NotImplementedError

  def _GetClientId(self, hostname):
    """Search GRR by hostname and get the latest active client.

    Args:
      hostname: hostname to search for.

    Returns:
      str: ID of most recently active client.

    Raises:
      RuntimeError: if no client ID found for hostname.
    """
    if self._CLIENT_ID_REGEX.match(hostname):
      return hostname

    # Search for the hostname in GRR
    syslog.syslog('Searching for client')
    self.console_out.VerboseOut('Searching for client: {0:s}'.format(hostname))
    search_result = self.grr_api.SearchClients(hostname)

    result = {}
    for client in search_result:
      client_id = client.client_id
      client_fqdn = client.data.os_info.fqdn
      client_last_seen_at = client.data.last_seen_at
      if hostname.lower() in client_fqdn.lower():
        result[client_id] = client_last_seen_at

    if not result:
      raise RuntimeError('Could not get client_id for {0:s}'.format(hostname))

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

    syslog.syslog('{0:s}: Found active client'.format(active_client_id))
    self.console_out.VerboseOut(
        'Found active client: {0:s}'.format(active_client_id))
    self.console_out.VerboseOut(
        'Client last seen: {0:s} ({1:d} minutes ago)'.format(
            last_seen_datetime.strftime('%Y-%m-%dT%H:%M:%S+0000'),
            last_seen_minutes))

    return active_client_id

  def _GetClient(self, client_id, reason, approvers):
    """Get GRR client dictionary and make sure valid approvals exist.

    Args:
      client_id: GRR client ID.
      reason: justification for GRR access.
      approvers: comma-separated list of GRR approval recipients.

    Returns:
      GRR API Client object

    Raises:
      ValueError: if no approvals exist and no approvers are specified.
    """
    client = self.grr_api.Client(client_id)
    self.console_out.VerboseOut('Checking for client approval')
    try:
      client.ListFlows()
    except grr_errors.AccessForbiddenError:
      syslog.syslog('{0:s}: No valid client approval found'.format(client_id))
      self.console_out.VerboseOut('No valid client approval found')
      if not approvers:
        raise ValueError(
            'GRR client needs approval but no approvers specified '
            '(hint: use --approvers)')
      self.console_out.VerboseOut(
          'Client approval request sent to: {0:s} (reason: {1:s})'.format(
              approvers, reason))
      self.console_out.VerboseOut(
          'Waiting for approval (this can take a while...)')
      # Send a request for approval and wait until there is a valid one
      # available in GRR.
      client.CreateApproval(reason=reason, notified_users=approvers)
      syslog.syslog('{0:s}: Request for client approval sent'.format(client_id))
      while True:
        try:
          client.ListFlows()
          break
        except grr_errors.AccessForbiddenError:
          time.sleep(self._CHECK_APPROVAL_INTERVAL_SEC)

    syslog.syslog('{0:s}: Client approval is valid'.format(client_id))
    self.console_out.VerboseOut('Client approval is valid')
    return client.Get()

  def _LaunchFlow(self, name, args):
    """Create specified flow, setting KeepAlive if requested.

    Args:
      name: string containing flow name.
      args: proto (*FlowArgs) for type of flow, as defined in GRR flow proto.

    Returns:
      string containing ID of launched flow
    """
    # Start the flow and get the flow ID
    flow = self._client.CreateFlow(name=name, args=args)
    flow_id = flow.flow_id
    syslog.syslog('Flow {0:s}: Scheduled'.format(flow_id))
    self.console_out.VerboseOut('Flow {0:s}: Scheduled'.format(flow_id))

    if self.keepalive:
      flow_name = 'KeepAlive'
      flow_args = flows_pb2.KeepAliveArgs()
      keepalive_flow = self._client.CreateFlow(name=flow_name, args=flow_args)
      syslog.syslog('KeepAlive scheduled')
      self.console_out.VerboseOut(
          'KeepAlive Flow:{0:s} scheduled'.format(keepalive_flow.flow_id))

    return flow_id

  def _AwaitFlow(self, flow_id):
    """Awaits flow completion.

    Args:
      flow_id: string containing ID of flow to await.

    Raises:
      RuntimeError: if flow error encountered.
    """
    # Wait for the flow to finish
    self.console_out.VerboseOut('Flow {0:s}: Waiting to finish'.format(flow_id))
    while True:
      try:
        status = self._client.Flow(flow_id).Get().data
      except grr_errors.UnknownError:
        raise RuntimeError(
            'Unable to stat flow {0:s} for host {1:s}'.format(
                flow_id, self.host))
      state = status.state
      if state == flows_pb2.FlowContext.ERROR:
        # TODO(jbn): If one artifact fails, what happens? Test.
        raise RuntimeError(
            'Flow {0:s}: FAILED! Backtrace from GRR:\n\n{1:s}'.format(
                flow_id, status.context.backtrace))
      elif state == flows_pb2.FlowContext.TERMINATED:
        syslog.syslog('Flow {0:s}: Complete'.format(flow_id))
        self.console_out.VerboseOut(
            'Flow {0:s}: Finished successfully'.format(flow_id))
        break
      time.sleep(self._CHECK_FLOW_INTERVAL_SEC)

    # Download the files collected by the flow
    syslog.syslog('Flow {0:s}: Downloading artifacts'.format(flow_id))
    self.console_out.VerboseOut(
        'Flow {0:s}: Downloading artifacts'.format(flow_id))
    collected_file_path = self._DownloadFiles(flow_id)

    if collected_file_path:
      syslog.syslog('Flow {0:s}: Downloaded artifacts'.format(flow_id))
      self.console_out.VerboseOut(
          'Flow {0:s}: Downloaded: {1:s}'.format(flow_id, collected_file_path))

  def PrintStatus(self):
    """Print status of flow.

    Raises:
      RuntimeError: if error encountered getting flow data.
    """
    self._client = self._GetClient(self._client_id, self.reason, self.approvers)
    try:
      status = self._client.Flow(self.flow_id).Get().data
    except grr_errors.UnknownError:
      raise RuntimeError(
          'Unable to stat flow {0:s} for host {1:s}'.format(
              self.flow_id, self.host))

    state = status.state
    if state == flows_pb2.FlowContext.ERROR:
      msg = 'ERROR'
    elif state == flows_pb2.FlowContext.TERMINATED:
      msg = 'Complete'
    elif state == flows_pb2.FlowContext.RUNNING:
      msg = 'Running...'
    self.console_out.StdOut(
        'Status of flow {0:s}: {1:s}\n'.format(self.flow_id, msg))

  def _DownloadFiles(self, flow_id):
    """Download files from the specified flow.

    Args:
      flow_id: GRR flow ID.

    Returns:
      str: path of downloaded files.
    """
    if not os.path.isdir(self.output_path):
      os.makedirs(self.output_path)

    output_file_path = os.path.join(
        self.output_path, '.'.join((flow_id, 'zip')))

    if os.path.exists(output_file_path):
      self.console_out.StdOut(
          '{0:s} already exists: Skipping'.format(output_file_path))
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
    self.console_out.VerboseOut(
        'Artifact collection name: {0:s}'.format(collection_name))
    return self._client.data.os_info.fqdn

  @staticmethod
  def launch_collector(
      hosts,
      flow_id,
      reason,
      grr_server_url,
      grr_auth,
      artifact_list=None,
      file_list=None,
      use_tsk=False,
      approvers=None,
      verbose=False,
      keepalive=False,
      status=False):
    """Launches a series of GRR Artifact collectors.

    Iterates over the values of hosts and starts a GRRArtifactCollector
    for each.

    Args:
      hosts: List of strings representing hosts to collect artifacts from.
      flow_id: ID of GRR flow to retrieve artifacts from.
      reason: justification for GRR access (usually a SEM ID).
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      artifact_list: comma-separated list of GRR-defined artifacts.
      file_list: comma-separated list of GRR file paths.
      use_tsk: toggle for use_tsk flag on GRR flow.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.
      keepalive: toggle for scheduling a KeepAlive flow.
      status: print the status of each collector.

    Returns:
      A list of started collectors for each path
    """
    collectors = []
    for hostname in hosts.split(','):
      host_collectors = []
      # Launch artifact collector if artifacts present or if no file/flow passed
      if artifact_list or not (file_list or flow_id):
        host_collectors.append(
            GRRArtifactCollector(
                hostname,
                reason,
                grr_server_url,
                grr_auth,
                artifact_list,
                use_tsk,
                approvers,
                verbose=verbose,
                keepalive=keepalive))
      if file_list:
        host_collectors.append(
            GRRFileCollector(
                hostname,
                reason,
                grr_server_url,
                grr_auth,
                file_list,
                approvers,
                verbose=verbose,
                keepalive=keepalive))
      if flow_id:
        host_collectors.append(
            GRRFlowCollector(
                hostname,
                reason,
                grr_server_url,
                grr_auth,
                flow_id,
                approvers,
                verbose=verbose))

      for collector in host_collectors:
        if flow_id and status:
          collector.PrintStatus()
        else:
          collector.start()
          collectors.append(collector)

    return collectors


class GRRArtifactCollector(GRRHostCollector):
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
      'OSXAppleSystemLogs', 'OSXAuditLogs', 'OSXBashHistory',
      'OSXInstallationHistory', 'OSXInstallationLog', 'OSXInstallationTime',
      'OSXLaunchAgents', 'OSXLaunchDaemons', 'OSXMiscLogs', 'OSXRecentItems',
      'OSXSystemLogs', 'OSXUserApplicationLogs', 'OSXQuarantineEvents'
  ]

  _DEFAULT_ARTIFACTS_WINDOWS = [
      'WindowsAppCompatCache', 'WindowsEventLogs', 'WindowsPrefetchFiles',
      'WindowsScheduledTasks', 'WindowsSearchDatabase',
      'WindowsSuperFetchFiles', 'WindowsSystemRegistryFiles',
      'WindowsUserRegistryFiles', 'WindowsXMLEventLogTerminalServices'
  ]

  def __init__(
      self,
      hostname,
      reason,
      grr_server_url,
      grr_auth,
      artifacts=None,
      use_tsk=False,
      approvers=None,
      verbose=False,
      keepalive=False):
    """Initializes a GRR artifact collector.

    Args:
      hostname: hostname of machine.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      artifacts: comma-separated list of GRR-defined artifacts.
      use_tsk: toggle for use_tsk flag on GRR flow.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.
      keepalive: toggle for scheduling a KeepAlive flow.
    """
    super(GRRArtifactCollector, self).__init__(
        hostname,
        reason,
        grr_server_url,
        grr_auth,
        approvers=approvers,
        verbose=verbose,
        keepalive=keepalive)
    self.artifacts = artifacts
    self.use_tsk = use_tsk

  def collect(self):
    """Collect the artifacts.

    Returns:
      list of tuples containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.

    Raises:
      RuntimeError: if no artifacts specified nor resolved by platform.
    """
    self._client = self._GetClient(self._client_id, self.reason, self.approvers)

    # Create a list of artifacts to collect.
    artifact_registry = {
        'Linux': self._DEFAULT_ARTIFACTS_LINUX,
        'Darwin': self._DEFAULT_ARTIFACTS_DARWIN,
        'Windows': self._DEFAULT_ARTIFACTS_WINDOWS
    }
    system_type = self._client.data.os_info.system
    self.console_out.VerboseOut('System type: {0:s}'.format(system_type))

    # If the list is supplied by the user via a flag, honor that.
    if self.artifacts:
      syslog.syslog('Artifacts to be collected: {0:s}'.format(self.artifacts))
      artifact_list = self.artifacts.split(',')
    else:
      syslog.syslog('Artifacts to be collected: Default')
      artifact_list = artifact_registry.get(system_type, None)

    if not artifact_list:
      raise RuntimeError('No artifacts to collect')
    flow_name = 'ArtifactCollectorFlow'
    flow_args = flows_pb2.ArtifactCollectorFlowArgs(
        artifact_list=artifact_list,
        use_tsk=self.use_tsk,
        ignore_interpolation_errors=True,
        apply_parsers=False,)
    self.console_out.VerboseOut(
        'Artifacts to collect: {0:s}'.format(artifact_list))
    flow_id = self._LaunchFlow(flow_name, flow_args)
    self._AwaitFlow(flow_id)
    return [(self.host, self.output_path)]


class GRRFileCollector(GRRHostCollector):
  """File collector for GRR flows.

  Attributes:
    files: comma-separated list of file paths.
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
  """

  def __init__(
      self,
      hostname,
      reason,
      grr_server_url,
      grr_auth,
      files=None,
      approvers=None,
      verbose=False,
      keepalive=False):
    """Initializes a GRR file collector.

    Args:
      hostname: hostname of machine.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      files: comma-separated list of file paths.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.
      keepalive: toggle for scheduling a KeepAlive flow.
    """
    super(GRRFileCollector, self).__init__(
        hostname,
        reason,
        grr_server_url,
        grr_auth=grr_auth,
        approvers=approvers,
        verbose=verbose,
        keepalive=keepalive)
    self.files = files

  def collect(self):
    """Collect the files.

    Returns:
      list of tuples containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.

    Raises:
      RuntimeError: if no files specified.
    """
    self._client = self._GetClient(self._client_id, self.reason, self.approvers)

    file_list = self.files.split(',')
    if not file_list:
      raise RuntimeError('File paths must be specified for FileFinder')
    syslog.syslog('Filefinder to collect {0:d} items'.format(len(file_list)))
    self.console_out.VerboseOut(
        'Files to be collected: {0:s}'.format(self.files))
    flow_name = 'FileFinder'
    flow_action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.DOWNLOAD,)
    flow_args = flows_pb2.FileFinderArgs(
        paths=file_list,
        action=flow_action,)
    flow_id = self._LaunchFlow(flow_name, flow_args)
    self._AwaitFlow(flow_id)
    return [(self.host, self.output_path)]


class GRRFlowCollector(GRRHostCollector):
  """Flow collector.

  Attributes:
    output_path: Path to where to store collected items.
    grr_api: GRR HTTP API client.
    host: Target of GRR collection.
    flow_id: ID of GRR flow to retrieve.
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
  """

  def __init__(
      self,
      hostname,
      reason,
      grr_server_url,
      grr_auth,
      flow_id=None,
      approvers=None,
      verbose=False):
    """Initializes a GRR flow collector.

    Args:
      hostname: hostname of machine.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      flow_id: ID of GRR flow to retrieve.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.
    """
    super(GRRFlowCollector, self).__init__(
        hostname,
        reason,
        grr_server_url,
        grr_auth,
        approvers=approvers,
        verbose=verbose)
    self.flow_id = flow_id

  def collect(self):
    """Collect the results.

    Returns:
      list: containing:
          str: human-readable description of the source of the collection. For
              example, the name of the source host.
          str: path to the collected data.

    Raises:
      RuntimeError: if no files specified
    """
    self._client = self._GetClient(self._client_id, self.reason, self.approvers)
    self._AwaitFlow(self.flow_id)
    return [(self.host, self.output_path)]


MODCLASS = [
    ('google_grr_hunt_collector', GRRHuntCollector),
    ('google_grr_hunt_artifact_collector', GRRHuntArtifactCollector),
    ('google_grr_hunt_file_collector',
     GRRHuntFileCollector), ('google_grr_hunt_downloader', GRRHuntDownloader),
    ('google_grr_host_collector',
     GRRHostCollector), ('google_grr_artifact_collector', GRRArtifactCollector),
    ('google_grr_file_collector',
     GRRFileCollector), ('google_grr_flow_collector', GRRFlowCollector)
]
