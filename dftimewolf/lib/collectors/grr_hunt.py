# -*- coding: utf-8 -*-
"""Definition of modules for collecting data from GRR Hunts."""

import os
import tempfile
import zipfile
from typing import List, Optional, Set, Tuple, Union

from grr_api_client.hunt import Hunt
from grr_response_proto import flows_pb2 as grr_flows
from grr_response_proto import osquery_pb2 as osquery_flows
from grr_response_proto.flows_pb2 import ArtifactCollectorFlowArgs
from grr_response_proto.flows_pb2 import FileFinderArgs
import yaml

from dftimewolf.lib import module
from dftimewolf.lib.collectors import grr_base
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


# TODO: GRRHunt should be extended by classes that actually implement
# the Process() method.
class GRRHunt(grr_base.GRRBaseModule, module.BaseModule):  # pylint: disable=abstract-method
  """This class groups functions generic to all GRR Hunt modules.

  Should be extended by the modules that interact with GRR hunts.

  Attributes:
    match_mode (str): match mode of the client rule set (ALL or ANY).
    client_operating_systems (Set[str]): a list of client OS types
        (win, osx or linux).
    client_labels (List[str]): a list of client labels.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str],
               critical: bool = False):
    module.BaseModule.__init__(self, state, name=name, critical=critical)
    grr_base.GRRBaseModule.__init__(self)
    self.match_mode = ""
    self.client_operating_systems : Set[str] = set()
    self.client_labels : List[str] = []

  def HuntSetup(
      self,
      match_mode: Optional[str],
      client_operating_systems: Optional[str],
      client_labels: Optional[str]) -> None:
    """Setup hunt client filter arguments.

    Args:
      match_mode (Optional[str]): match mode of the client rule set (ALL or
          ANY).
      client_operating_systems (Optional[str]): a comma separated list of client
          OS types (win, osx or linux).
      client_labels (Optional[str]): a comma separated list of client labels.
    """
    if match_mode:
      if match_mode.lower() not in ('all', 'any'):
        self.ModuleError(f'Unknown match mode {self.match_mode}', critical=True)

      self.match_mode = match_mode.lower()

    if client_operating_systems:
      normalised_client_operating_systems = set(
          os.lower() for os in client_operating_systems.split(',')
          if os.lower() in ('win', 'osx', 'linux'))

      if not normalised_client_operating_systems:
        self.ModuleError('No valid client operating systems in argument '
                         f'"{client_operating_systems}"', critical=True)

      self.client_operating_systems = normalised_client_operating_systems

    if client_labels:
      self.client_labels = list(client_labels.split(','))

  # TODO: change object to more specific GRR type information.
  def _CreateHunt(
      self,
      name: str,
      args: Union[
          ArtifactCollectorFlowArgs,
          FileFinderArgs,
          osquery_flows.OsqueryFlowArgs]
    ) -> Hunt:
    """Creates a GRR hunt.

    Args:
      name (str): name of the hunt.
      args (object): arguments specific for type of flow, as defined in GRR
          flow proto (FlowArgs).

    Returns:
      object: a GRR hunt object.

    Raises:
      DFTimewolfError: if approval is needed and approvers were not specified.
    """
    runner_args = self.grr_api.types.CreateHuntRunnerArgs()
    runner_args.description = self.reason

    if self.match_mode:
      if self.match_mode == 'any':
        match_mode = runner_args.client_rule_set.MATCH_ANY
      elif self.match_mode == 'all':
        match_mode = runner_args.client_rule_set.MATCH_ALL

      runner_args.client_rule_set.match_mode = match_mode

    if self.client_labels:
      for client_label in self.client_labels:
        label_rule = runner_args.client_rule_set.rules.add()

        label_rule.rule_type = label_rule.LABEL
        label_rule.label.label_names.append(client_label)

    if self.client_operating_systems:
      for client_operating_system in self.client_operating_systems:
        os_rule = runner_args.client_rule_set.rules.add()

        os_rule.rule_type = os_rule.OS

        if client_operating_system == 'win':
          os_rule.os.os_windows = True
        elif client_operating_system == 'osx':
          os_rule.os.os_darwin = True
        elif client_operating_system == 'linux':
          os_rule.os.os_linux = True

    hunt = self.grr_api.CreateHunt(
        flow_name=name, flow_args=args, hunt_runner_args=runner_args)

    self.logger.success('{0!s}: Hunt created'.format(hunt.hunt_id))
    self._WrapGRRRequestWithApproval(hunt, hunt.Start, self.logger)
    return hunt


class GRRHuntArtifactCollector(GRRHunt):
  """Artifact collector for GRR hunts.

  Attributes:
    reason (str): justification for GRR access.
    approvers (str): comma-separated GRR approval recipients.
    artifacts (str): comma-separated list of GRR-defined artifacts.
    use_tsk (bool): True if GRR should use Sleuthkit (TSK) to collect file
        system artifacts.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str] = None,
               critical: bool = False) -> None:
    """Initializes a GRR artifact collector hunt.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (bool): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GRRHuntArtifactCollector, self).__init__(
        state, name=name, critical=critical)
    self.artifacts = []  # type: List[str]
    self.use_tsk = False
    self.hunt = None  # type: Hunt
    self.max_file_size = 5*1024*1024*1024  # 5 GB

  # pylint: disable=arguments-differ,disable=too-many-arguments
  def SetUp(self,
            artifacts: str,
            use_tsk: bool,
            reason: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            max_file_size: str,
            approvers: str,
            verify: bool,
            match_mode: str,
            client_operating_systems: str,
            client_labels: str) -> None:
    """Initializes a GRR Hunt artifact collector.

    Args:
      artifacts (str): comma-separated list of GRR-defined artifacts.
      use_tsk (bool): True if GRR should use Sleuthkit (TSK) to collect file
          system artifacts.
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      approvers (str): comma-separated GRR approval recipients.
      verify (bool): True to indicate GRR server's x509 certificate
          should be verified.
      match_mode (str): match mode of the client rule set.
          (all/ALL or any/ANY).
      client_operating_systems (str): a comma separated list of
          client OS types (win, osx or linux).
      client_labels (str): a comma separated list of client labels.
    """
    self.GrrSetUp(reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify)

    self.artifacts = [item.strip() for item in artifacts.strip().split(',')]
    if not artifacts:
      self.ModuleError('No artifacts were specified.', critical=True)
    self.use_tsk = use_tsk
    if max_file_size:
      self.max_file_size = int(max_file_size)

    self.HuntSetup(match_mode, client_operating_systems, client_labels)

  def Process(self) -> None:
    """Starts a new Artifact Collection GRR hunt.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    self.logger.info('Artifacts to be collected: {0!s}'.format(self.artifacts))
    hunt_args = grr_flows.ArtifactCollectorFlowArgs(
        artifact_list=self.artifacts,
        use_tsk=self.use_tsk,
        ignore_interpolation_errors=True,
        apply_parsers=False,
        max_file_size=self.max_file_size)
    self._CreateHunt('ArtifactCollectorFlow', hunt_args)


class GRRHuntFileCollector(GRRHunt):
  """File collector for GRR hunts.

  Attributes:
    reason (str): justification for GRR access.
    approvers (str): comma-separated GRR approval recipients.
    file_path_list: comma-separated list of file paths.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str] = None,
               critical: bool = False) -> None:
    """Initializes a GRR file collector hunt.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (bool): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GRRHuntFileCollector, self).__init__(
        state, name=name, critical=critical)
    self.file_path_list = []  # type: List[str]
    self.max_file_size = 5*1024*1024*1024  # 5 GB

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            file_path_list: str,
            reason: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            max_file_size: str,
            approvers: str,
            verify: bool,
            match_mode: str,
            client_operating_systems: str,
            client_labels: str) -> None:
    """Initializes a GRR Hunt file collector.

    Args:
      file_path_list (str): comma-separated file paths.
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      max_file_size (str): Maximum file size to collect (in bytes).
      approvers (str): comma-separated GRR approval recipients.
      verify (bool): True to indicate GRR server's x509 certificate
          should be verified.
      match_mode (str): match mode of the client rule set.
          (all/ALL or any/ANY).
      client_operating_systems (str): a comma separated list of
          client OS types (win, osx or linux).
      client_labels (str): a comma separated list of client labels.
    """
    self.GrrSetUp(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify)
    self.file_path_list = [item.strip() for item
                           in file_path_list.strip().split(',')]
    if not file_path_list:
      self.ModuleError('Files must be specified for hunts', critical=True)
    if max_file_size:
      self.max_file_size = int(max_file_size)

    self.HuntSetup(match_mode, client_operating_systems, client_labels)

  # TODO: this method does not raise itself, indicate what function call does.
  def Process(self) -> None:
    """Starts a new File Finder GRR hunt.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    self.logger.info(
        'Hunt to collect {0:d} items'.format(len(self.file_path_list)))
    self.logger.info(
        'Files to be collected: {0!s}'.format(self.file_path_list))
    hunt_action = grr_flows.FileFinderAction(
        action_type=grr_flows.FileFinderAction.DOWNLOAD,
        download=grr_flows.FileFinderDownloadActionOptions(
            max_size=self.max_file_size)
        )
    hunt_args = grr_flows.FileFinderArgs(
        paths=self.file_path_list,
        action=hunt_action)
    self._CreateHunt('FileFinder', hunt_args)


class GRRHuntOsqueryCollector(GRRHunt):
  """Osquery collector for a GRR Hunt."""

  DEFAULT_OSQUERY_TIMEOUT_MILLIS = 3000000

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str] = None,
               critical: bool = False) -> None:
    """Initializes a GRR file collector hunt.
    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (bool): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
      osquery_statement (str): osquery statement.
    """
    super(GRRHuntOsqueryCollector, self).__init__(
        state, name=name, critical=critical)
    self.timeout_millis = self.DEFAULT_OSQUERY_TIMEOUT_MILLIS
    self.ignore_stderr_errors = True
    self.osquery_statement = ""

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            osquery_statement: str,
            reason: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            approvers: str,
            verify: bool,
            match_mode: str,
            client_operating_systems: str,
            client_labels: str) -> None:
    """Initializes a GRR Hunt Osquery collector.

    Args:
      osquery_statement (str): osquery statement.
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      approvers (str): comma-separated GRR approval recipients.
      verify (bool): True to indicate GRR server's x509 certificate
          should be verified.
      match_mode (str): match mode of the client rule set.
          (all/ALL or any/ANY).
      client_operating_systems (str): a comma separated list of
          client OS types (win, osx or linux).
      client_labels (str): a comma separated list of client labels.
    """
    if not osquery_statement:
      self.ModuleError('Osquery statement cannot be null', critical=True)

    if not osquery_statement.upper().startswith('SELECT '):
      self.ModuleError(
          'Osquery statement doesn\'t start with SELECT', critical=True)

    self.osquery_statement = osquery_statement

    self.GrrSetUp(
        reason=reason,
        grr_server_url=grr_server_url,
        grr_username=grr_username,
        grr_password=grr_password,
        approvers=approvers,
        verify=verify)

    self.HuntSetup(match_mode, client_operating_systems, client_labels)

  def Process(self) -> None:
    """Starts a new Osquery GRR hunt."""
    hunt_args = osquery_flows.OsqueryFlowArgs()
    hunt_args.query = self.osquery_statement
    hunt_args.timeout_millis = self.timeout_millis
    hunt_args.ignore_stderr_errors = self.ignore_stderr_errors

    self._CreateHunt('OsqueryHunt', hunt_args)


class GRRHuntDownloader(GRRHunt):
  """Downloads results from a GRR Hunt.

  Attributes:
    reason (str): justification for GRR access.
    approvers (str): comma-separated GRR approval recipients.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str] = None,
               critical: bool = False) -> None:
    """Initializes a GRR hunt results downloader.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (bool): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GRRHuntDownloader, self).__init__(state, name=name, critical=critical)
    self.hunt_id = str()
    self.output_path = str()

  # pylint: disable=arguments-differ
  def SetUp(self,
            hunt_id: str,
            reason: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            approvers: str,
            verify: bool) -> None:
    """Initializes a GRR Hunt file collector.

    Args:
      hunt_id (str): GRR identifier of the hunt for which to download results.
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      approvers (str): comma-separated GRR approval recipients.
      verify (bool): True to indicate GRR server's x509 certificate
          should be verified.
    """
    self.GrrSetUp(
        reason, grr_server_url, grr_username, grr_password,
        approvers=approvers, verify=verify)
    self.hunt_id = hunt_id
    self.output_path = tempfile.mkdtemp()

  # TODO: change object to more specific GRR type information.
  def _CollectHuntResults(self, hunt: Hunt) -> List[Tuple[str, str]]:
    """Downloads the current set of files in results.

    Args:
      hunt (object): GRR hunt object to download files from.

    Returns:
      list[tuple[str, str]]: pairs of human-readable description of the source
          of the collection, for example the name of the source host, and
          the path to the collected data.

    Raises:
      DFTimewolfError: if approval is needed and approvers were not specified.
    """
    if not os.path.isdir(self.output_path):
      os.makedirs(self.output_path)

    output_file_path = os.path.join(
        self.output_path, '.'.join((self.hunt_id, 'zip')))

    if os.path.exists(output_file_path):
      self.logger.info(
          '{0:s} already exists: Skipping'.format(output_file_path))
      return []

    self._WrapGRRRequestWithApproval(
        hunt, self._GetAndWriteArchive, self.logger, hunt, output_file_path)

    results = self._ExtractHuntResults(output_file_path)
    self.logger.success('Wrote results of {0:s} to {1:s}'.format(
        hunt.hunt_id, output_file_path))
    return results

  # TODO: change object to more specific GRR type information.
  def _GetAndWriteArchive(self, hunt: Hunt, output_file_path: str) -> None:
    """Retrieves and writes a hunt archive.

    Function is necessary for the _WrapGRRRequestWithApproval to work.

    Args:
      hunt (object): GRR hunt object.
      output_file_path (str): output path where to write the Hunt Archive.
    """
    hunt_archive = hunt.GetFilesArchive()
    hunt_archive.WriteToFile(output_file_path)

  def _GetClientFQDN(self, client_info_contents: bytes) -> Tuple[str, str]:
    """Extracts a GRR client's FQDN from its client_info.yaml file.

    Args:
      client_info_contents (str): contents of the client_info.yaml file.

    Returns:
      tuple[str, str]: client identifier and client FQDN.
    """
    # TODO: handle incorrect file contents.
    yamldict = yaml.safe_load(client_info_contents)
    fqdn = yamldict['os_info']['fqdn']
    client_id = yamldict['client_id']
    return client_id, fqdn

  def _ExtractHuntResults(self, output_file_path: str) -> List[Tuple[str, str]]:
    """Opens a hunt output archive and extract files.

    Args:
      output_file_path (str): path where the hunt results archive file is
          downloaded to.

    Returns:
      list[tuple[str, str]]: pairs of names of the GRR clients, from which
          the files were collected, and path where the files were downloaded to.
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
            client_id, fqdn = self._GetClientFQDN(archive.read(f))
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
              self.logger.warning('Extraction error: {0:s}'.format(exception))
              return []

    except OSError as exception:
      msg = 'Error manipulating file {0:s}: {1!s}'.format(
          output_file_path, exception)
      self.ModuleError(msg, critical=True)
    except zipfile.BadZipfile as exception:
      msg = 'Bad zipfile {0:s}: {1!s}'.format(
          output_file_path, exception)
      self.ModuleError(msg, critical=True)

    try:
      os.remove(output_file_path)
    except OSError as exception:
      self.logger.warning(
          'Output path {0:s} could not be removed: {1:s}'.format(
              output_file_path, exception))

    # Translate GRR client IDs to FQDNs with the information retrieved
    # earlier
    fqdn_collection_paths = []
    for client_id, path in collection_paths:
      fqdn = client_id_to_fqdn.get(client_id, client_id)
      fqdn_collection_paths.append((fqdn, path))

    if not fqdn_collection_paths:
      self.ModuleError(
          'Nothing was extracted from the hunt archive', critical=True)

    return fqdn_collection_paths

  def Process(self) -> None:
    """Downloads the results of a GRR hunt.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    hunt = self.grr_api.Hunt(self.hunt_id).Get()
    for description, path in self._CollectHuntResults(hunt):
      container = containers.File(name=description, path=path)
      self.state.StoreContainer(container)


modules_manager.ModulesManager.RegisterModules([
    GRRHuntArtifactCollector,
    GRRHuntFileCollector,
    GRRHuntOsqueryCollector,
    GRRHuntDownloader])
