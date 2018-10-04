# -*- coding: utf-8 -*-
"""Definition of modules for collecting data from GRR Hunts."""

from __future__ import print_function
from __future__ import unicode_literals

import os
import tempfile
import zipfile
import yaml

from grr_response_proto import flows_pb2

from dftimewolf.lib.collectors import grr_base


# GRRHunt should be extended by classes that actually implement the process()
# method
class GRRHunt(grr_base.GRRBaseModule):  # pylint: disable=abstract-method
  """This class groups functions generic to all GRR Hunt modules.

  Should be extended by the modules that interact with GRR hunts.
  """

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
    print('{0:s}: Hunt created'.format(hunt.hunt_id))
    self._check_approval_wrapper(hunt, hunt.Start)
    return hunt


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
            reason, grr_server_url, grr_username, grr_password, approvers=None,
            verify=True):
    """Initializes a GRR Hunt artifact collector.

    Args:
      artifacts: str, comma-separated list of GRR-defined artifacts.
      use_tsk: toggle for use_tsk flag.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_username: GRR username.
      grr_password: GRR password.
      approvers: str, comma-separated list of GRR approval recipients.
      verify: boolean, whether to verify the GRR server's x509 certificate.
    """
    super(GRRHuntArtifactCollector, self).setup(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify)

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

    print('Artifacts to be collected: {0:s}'.format(self.artifacts))
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
    file_path_list: comma-separated list of file paths.
  """

  def __init__(self, state):
    super(GRRHuntFileCollector, self).__init__(state)
    self.file_path_list = None

  # pylint: disable=arguments-differ
  def setup(self,
            file_path_list,
            reason, grr_server_url, grr_username, grr_password, approvers=None,
            verify=True):
    """Initializes a GRR Hunt file collector.

    Args:
      file_path_list: comma-separated list of file paths.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_username: GRR username.
      grr_password: GRR password.
      approvers: comma-separated list of GRR approval recipients.
      verify: boolean, whether to verify the GRR server's x509 certificate.
    """
    super(GRRHuntFileCollector, self).setup(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify)
    self.file_path_list = [item.strip() for item
                           in file_path_list.strip().split(',')]
    if not file_path_list:
      self.state.add_error('Files must be specified for hunts', critical=True)

  def process(self):
    """Construct and start a new File hunt.

    Returns:
      The newly created GRR hunt object.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    print('Hunt to collect {0:d} items'.format(len(self.file_path_list)))
    print('Files to be collected: {0:s}'.format(self.file_path_list))
    hunt_action = flows_pb2.FileFinderAction(
        action_type=flows_pb2.FileFinderAction.DOWNLOAD)
    hunt_args = flows_pb2.FileFinderArgs(
        paths=self.file_path_list, action=hunt_action)
    return self._create_hunt('FileFinder', hunt_args)


class GRRHuntDownloader(GRRHunt):
  """Downloads results from a GRR Hunt.

  Attributes:
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
  """

  def __init__(self, state):
    super(GRRHuntDownloader, self).__init__(state)
    self.hunt_id = None
    self.output_path = None

  # pylint: disable=arguments-differ
  def setup(self,
            hunt_id,
            reason, grr_server_url, grr_username, grr_password, approvers=None,
            verify=True):
    """Initializes a GRR Hunt file collector.

    Args:
      hunt_id: Hunt ID to download results from.
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_username: GRR username.
      grr_password: GRR password.
      approvers: comma-separated list of GRR approval recipients.
      verify: boolean, whether to verify the GRR server's x509 certificate.
    """
    super(GRRHuntDownloader, self).setup(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify)
    self.hunt_id = hunt_id
    self.output_path = tempfile.mkdtemp()

  def collect_hunt_results(self, hunt):
    """Download current set of files in results.

    Args:
      hunt: The GRR hunt object to download files from.

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
      print('{0:s} already exists: Skipping'.format(output_file_path))
      return None

    self._check_approval_wrapper(
        hunt, self._get_and_write_archive, hunt, output_file_path)

    results = self._extract_hunt_results(output_file_path)
    print('Wrote results of {0:s} to {1:s}'.format(
        hunt.hunt_id, output_file_path))
    return results

  def _get_and_write_archive(self, hunt, output_file_path):
    """Gets and writes a hunt archive.

    Function is necessary for the _check_approval_wrapper to work.

    Args:
      hunt: The GRR hunt object.
      output_file_path: The output path where to write the Hunt Archive.
    """
    hunt_archive = hunt.GetFilesArchive()
    hunt_archive.WriteToFile(output_file_path)

  def _get_client_fqdn(self, client_info_contents):
    """Extracts a GRR client's FQDN from its client_info.yaml file.

    Args:
      client_info_contents: The contents of the client_info.yaml file.

    Returns:
      A (str, str) tuple representing client ID and client FQDN.
    """
    yamldict = yaml.safe_load(client_info_contents)
    fqdn = yamldict['system_info']['fqdn']
    client_id = yamldict['client_id'].split('/')[1]
    return client_id, fqdn

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
    client_ids = set()
    client_id_to_fqdn = {}
    hunt_dir = None
    try:
      with zipfile.ZipFile(output_file_path) as archive:
        items = archive.infolist()
        for f in items:

          if not hunt_dir:
            hunt_dir = f.filename.split('/')[0]

          # If we're dealing with client_info.yaml, use it to build a client
          # ID to FQDN correspondence table & skip extraction.
          if f.filename.split('/')[-1] == 'client_info.yaml':
            client_id, fqdn = self._get_client_fqdn(archive.read(f))
            client_id_to_fqdn[client_id] = fqdn
            continue

          client_id = f.filename.split('/')[1]
          if client_id.startswith('C.'):
            if client_id not in client_ids:
              client_directory = os.path.join(self.output_path,
                                              hunt_dir, client_id)
              collection_paths.append((client_id, client_directory))
              client_ids.add(client_id)
            try:
              archive.extract(f, self.output_path)
            except KeyError as exception:
              print('Extraction error: {0:s}'.format(exception))
              return []

    except OSError as exception:
      msg = 'Error manipulating file {0:s}: {1:s}'.format(
          output_file_path, exception)
      self.state.add_error(msg, critical=True)
      return []
    except zipfile.BadZipfile as exception:
      msg = 'Bad zipfile {0:s}: {1:s}'.format(
          output_file_path, exception)
      self.state.add_error(msg, critical=True)
      return []

    try:
      os.remove(output_file_path)
    except OSError as exception:
      print('Output path {0:s} could not be removed: {1:s}'.format(
          output_file_path, exception))

    # Translate GRR client IDs to FQDNs with the information retrieved
    # earlier
    fqdn_collection_paths = []
    for client_id, path in collection_paths:
      fqdn = client_id_to_fqdn.get(client_id, client_id)
      fqdn_collection_paths.append((fqdn, path))

    if not fqdn_collection_paths:
      self.state.add_error('Nothing was extracted from the hunt archive',
                           critical=True)
      return []

    return fqdn_collection_paths

  def process(self):
    """Construct and start a new File hunt.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    hunt = self.grr_api.Hunt(self.hunt_id).Get()
    self.state.output = self.collect_hunt_results(hunt)
