# -*- coding: utf-8 -*-
"""Collects artifacts with GRR."""

from __future__ import unicode_literals

import os
import zipfile

from grr_response_proto import flows_pb2

from dftimewolf.lib.collectors.grr_base import GRRBaseModule

class GRRHunt(GRRBaseModule):
  """This class groups functions generic to all GRR Hunt modules."""

  def _create_hunt(self, name, args):
    """Create specified hunt.

    Args:
      name: string containing hunt name.
      args: proto (*FlowArgs) for type of hunt, as defined in GRR flow proto.

    Returns:
      The newly created GRR hunt object.

    Raises:
      ValueError: if approval is needed and approvers were not specified.
    """
    runner_args = self.grr_api.types.CreateHuntRunnerArgs()
    runner_args.description = self.reason
    hunt = self.grr_api.CreateHunt(
        flow_name=name, flow_args=args, hunt_runner_args=runner_args)
    print '{0:s}: Hunt created'.format(hunt.hunt_id)
    self._check_approval_wrapper(hunt, hunt.Start)
    return hunt

  def collect_hunt_results(self):
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
      print '{0:s} already exists: Skipping'.format(output_file_path)
      return None

    hunt_archive = self._check_approval_wrapper(
        self.hunt, self.hunt.GetFilesArchive)
    hunt_archive.WriteToFile(output_file_path)
    return self._extract_hunt_results(output_file_path)

  def _extract_hunt_results(self, output_file_path):
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
      for f in items:
        client_id = f.filename.split('/')[1]
        if client_id.startswith('C.'):
          client = self.grr_api.Client(client_id).Get()
          client_name = client.data.os_info.fqdn
          client_directory = os.path.join(self.output_path, client_id)
          if not os.path.isdir(client_directory):
            os.makedirs(client_directory)
          collection_paths.append((client_name, client_directory))
          try:
            archive.extract(f, client_directory)
          except KeyError as exception:
            self.console_out.StdErr('Extraction error: {0:s}'.format(exception))
            return []

    os.remove(output_file_path)

    return collection_paths

  def print_status(self):
    """Print status of hunt."""
    status = self.grr_api.Hunt(self.hunt_id).Get().data
    print 'Status of hunt {0:s}'.format(self.hunt_id)
    print 'Total clients: {0:d}'.format(status.all_clients_count)
    print 'Completed clients: {0:d}'.format(status.completed_clients_count)
    print 'Outstanding clients: {0:d}'.format(status.remaining_clients_count)


class GRRHuntArtifactCollector(GRRHunt):
  """Artifact collector for GRR hunts.

  Attributes:
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
    artifacts: comma-separated list of GRR-defined artifacts.
    use_tsk: toggle for use_tsk flag.
  """

  def __init__(self, state):
    super(GRRHuntArtifactCollector, self).__init__(state)
    self.artifacts = None
    self.use_tsk = None
    self.hunt = None

  # pylint: disable=arguments-differ
  def setup(self,
            artifacts, use_tsk,
            reason, grr_server_url, grr_auth, approvers=None):
    """Initializes a GRR Hunt artifact collector.

    Args:
      artifacts: str, comma-separated list of GRR-defined artifacts.
      use_tsk: toggle for use_tsk flag.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      approvers: str, comma-separated list of GRR approval recipients.
    """
    super(GRRHuntArtifactCollector, self).setup(
        reason, grr_server_url, grr_auth, approvers=approvers)

    self.artifacts = [item.strip() for item in artifacts.strip().split(',')]
    if not artifacts:
      self.state.add_error('No artifacts were specified.', critical=True)
    self.use_tsk = use_tsk

  def process(self):
    """Construct and start new Artifact Collection hunt.

    Returns:
      The newly created GRR hunt object.

    Raises:
      RuntimeError: if no items specified for collection.
    """

    print 'Artifacts to be collected: {0:s}'.format(self.artifacts)
    hunt_args = flows_pb2.ArtifactCollectorFlowArgs(
        artifact_list=self.artifacts,
        use_tsk=self.use_tsk,
        ignore_interpolation_errors=True,
        apply_parsers=False,)
    return self._create_hunt('ArtifactCollectorFlow', hunt_args)


class GRRHuntFileCollector(GRRHunt):
  """File collector for GRR hunts.

  Attributes:
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
    file_list: comma-separated list of file paths.
  """

  def __init__(self, state):
    super(GRRHuntFileCollector, self).__init__(state)
    self.file_list = None

  # pylint: disable=arguments-differ
  def setup(self,
            file_list,
            reason, grr_server_url, grr_auth, approvers=None):
    """Initializes a GRR Hunt file collector.

    Args:
      file_list: comma-separated list of file paths.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      approvers: comma-separated list of GRR approval recipients.
      verbose: toggle for verbose output.
    """
    super(GRRHuntFileCollector, self).__init__(
        reason, grr_server_url, grr_auth, approvers=approvers)
    self.file_list = [item.strip() for item in file_list.strip().split(',')]
    if not file_list:
      self.state.add_error('Files must be specified for hunts', critical=True)

  def process(self):
    """Construct and start a new File hunt.

    Returns:
      The newly created GRR hunt object.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    print 'Hunt to collect {0:d} items'.format(len(self.file_list))
    print 'Files to be collected: {0:s}'.format(self.file_list)
    hunt_action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.DOWNLOAD)
    hunt_args = flows_pb2.FileFinderArgs(
        paths=self.file_list, action=hunt_action)
    return self._create_hunt('FileFinder', hunt_args)
