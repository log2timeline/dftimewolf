# -*- coding: utf-8 -*-
"""Definition of modules for collecting data from GRR Hunts."""

import os
import re
import tempfile
import zipfile
from typing import List, Optional, Set, Tuple, Union, Dict

import pandas as pd
import yaml
from grr_api_client.hunt import Hunt
from grr_response_proto import flows_pb2 as grr_flows
from grr_response_proto import osquery_pb2 as osquery_flows

from dftimewolf.lib import module
from dftimewolf.lib.collectors import grr_base
from dftimewolf.lib.containers import containers
from dftimewolf.lib.errors import DFTimewolfError
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
    self.match_mode: str = ""
    self.client_operating_systems : Set[str] = set()
    self.client_labels : List[str] = []
    self.hunt_runner_args = None  # type: Optional[grr_flows.HuntRunnerArgs]
    self.hunt_description: str = ''

  def HuntSetup(
      self,
      match_mode: Optional[str],
      client_operating_systems: Optional[str],
      client_labels: Optional[str],
      extra_hunt_runner_args: Union[Dict[str, Union[str, int]], None] = None
    ) -> None:
    """Setup hunt client filter arguments.

    Args:
      match_mode: match mode of the client rule set (ALL or ANY).
      client_operating_systems: a comma separated list of client OS types (win,
          osx or linux).
      client_labels: a comma separated list of client labels.
      extra_hunt_runner_args: extra arguments to pass to the hunt runner proto.
    """
    if not extra_hunt_runner_args:
      extra_hunt_runner_args = {}

    runner_args = self.grr_api.types.CreateHuntRunnerArgs()
    runner_args.description = self.hunt_description or self.reason

    if match_mode:
      if match_mode.lower() not in ('all', 'any'):
        self.ModuleError(f'Unknown match mode {self.match_mode}', critical=True)
      match_mode = match_mode.lower()
      if match_mode == 'any':
        match_mode = runner_args.client_rule_set.MATCH_ANY
      elif match_mode == 'all':
        match_mode = runner_args.client_rule_set.MATCH_ALL
      runner_args.client_rule_set.match_mode = match_mode

    if client_operating_systems:
      normalised_client_operating_systems = set(
          os.lower() for os in client_operating_systems.split(',')
          if os.lower() in ('win', 'osx', 'linux'))
      os_rule = runner_args.client_rule_set.rules.add()
      os_rule.rule_type = os_rule.OS
      os_rule.os.os_windows = 'win' in normalised_client_operating_systems
      os_rule.os.os_darwin = 'osx' in normalised_client_operating_systems
      os_rule.os.os_linux = 'linux' in normalised_client_operating_systems

    if client_labels:
      for client_label in list(client_labels.split(',')):
        label_rule = runner_args.client_rule_set.rules.add()
        label_rule.rule_type = label_rule.LABEL
        label_rule.label.label_names.append(client_label)

    for key, value in extra_hunt_runner_args.items():
      setattr(runner_args, key, value)

    self.hunt_runner_args = runner_args


  # TODO: change object to more specific GRR type information.
  def _CreateAndStartHunt(
      self,
      flow_name: str,
      flow_args: Union[
          grr_flows.ArtifactCollectorFlowArgs,
          grr_flows.FileFinderArgs,
          osquery_flows.OsqueryFlowArgs,
          grr_flows.YaraProcessScanRequest]
    ) -> Hunt:
    """Creates a GRR hunt and starts it, waiting for approvals.

    Args:
      name (str): name of the hunt.
      args (object): arguments specific for type of flow, as defined in GRR
          flow proto (FlowArgs).

    Returns:
      object: a GRR hunt object.

    Raises:
      DFTimewolfError: if approval is needed and approvers were not specified.
    """
    hunt = self.grr_api.CreateHunt(
        flow_name=flow_name,
        flow_args=flow_args,
        hunt_runner_args=self.hunt_runner_args)

    self.PublishMessage(f'{hunt.hunt_id}: Hunt created')
    try:
      self._WrapGRRRequestWithApproval(hunt, hunt.Start, self.logger)
    except DFTimewolfError as exception:
      self.ModuleError(exception.message, critical=exception.critical)
    return hunt


class GRRHuntArtifactCollector(GRRHunt):
  """Artifact collector for GRR hunts.

  Attributes:
    reason (str): justification for GRR access.
    approvers (str): comma-separated GRR approval recipients.
    artifacts (str): comma-separated list of GRR-defined artifacts.
    use_raw_filesystem_access (bool): True if GRR should use raw disk access
        to collect file system artifacts.
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
    self.use_raw_filesystem_access = False
    self.hunt = None  # type: Hunt
    self.max_file_size = 5*1024*1024*1024  # 5 GB

  # pylint: disable=arguments-differ,disable=too-many-arguments
  def SetUp(self,
            artifacts: str,
            use_raw_filesystem_access: bool,
            reason: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            max_file_size: str,
            approvers: str,
            verify: bool,
            match_mode: Optional[str],
            client_operating_systems: Optional[str],
            client_labels: Optional[str]) -> None:
    """Initializes a GRR Hunt artifact collector.

    Args:
      artifacts (str): comma-separated list of GRR-defined artifacts.
      use_raw_filesystem_access (bool): True if GRR should use raw disk access
          to collect file system artifacts.
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
    self.GrrSetUp(
        reason, grr_server_url, grr_username, grr_password, approvers=approvers,
        verify=verify, message_callback=self.PublishMessage)

    self.artifacts = [item.strip() for item in artifacts.strip().split(',')]
    if not artifacts:
      self.ModuleError('No artifacts were specified.', critical=True)
    self.use_raw_filesystem_access = use_raw_filesystem_access
    if max_file_size:
      self.max_file_size = int(max_file_size)

    self.HuntSetup(match_mode, client_operating_systems, client_labels)

  def Process(self) -> None:
    """Starts a new Artifact Collection GRR hunt.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    self.logger.info(f'Artifacts to be collected: {self.artifacts!s}')
    hunt_args = grr_flows.ArtifactCollectorFlowArgs(
        artifact_list=self.artifacts,
        use_raw_filesystem_access=self.use_raw_filesystem_access,
        ignore_interpolation_errors=True,
        apply_parsers=False,
        max_file_size=self.max_file_size)
    self._CreateAndStartHunt('ArtifactCollectorFlow', hunt_args)


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
            match_mode: Optional[str],
            client_operating_systems: Optional[str],
            client_labels: Optional[str]) -> None:
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
        reason, grr_server_url, grr_username, grr_password, approvers=approvers,
        verify=verify, message_callback=self.PublishMessage)
    self.file_path_list = [item.strip() for item
                           in file_path_list.strip().split(',')]
    if max_file_size:
      self.max_file_size = int(max_file_size)

    self.HuntSetup(match_mode, client_operating_systems, client_labels)

  def PreProcess(self) -> None:
    """Load File paths from containers and check there are files to download."""
    for file_container in self.GetContainers(
        container_class=containers.FSPath):
      self.file_path_list.append(file_container.path)

    if not self.file_path_list:
      self.ModuleError('Files must be specified for hunts', critical=True)

  # TODO: this method does not raise itself, indicate what function call does.
  def Process(self) -> None:
    """Starts a new File Finder GRR hunt.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    self.logger.info(
        f'Hunt to collect {len(self.file_path_list):d} items')
    self.logger.info(
        f'Files to be collected: {self.file_path_list!s}')
    hunt_action = grr_flows.FileFinderAction(
        action_type=grr_flows.FileFinderAction.DOWNLOAD,
        download=grr_flows.FileFinderDownloadActionOptions(
            max_size=self.max_file_size)
        )
    hunt_args = grr_flows.FileFinderArgs(
        paths=self.file_path_list,
        action=hunt_action)
    self._CreateAndStartHunt('FileFinder', hunt_args)


class GRRHuntOsqueryCollector(GRRHunt):
  """Osquery collector for a GRR Hunt.

  Attributes:
    timeout_millis (int): the number of milliseconds before osquery timeouts.
    ignore_stderr_errors (bool): ignore stderr errors from osquery.
  """

  DEFAULT_OSQUERY_TIMEOUT_MILLIS = 300000

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
    super(GRRHuntOsqueryCollector, self).__init__(
        state, name=name, critical=critical)
    self.timeout_millis = self.DEFAULT_OSQUERY_TIMEOUT_MILLIS
    self.ignore_stderr_errors = True

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            reason: str,
            timeout_millis: int,
            ignore_stderr_errors: bool,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            approvers: str,
            verify: bool,
            match_mode: Optional[str],
            client_operating_systems: Optional[str],
            client_labels: Optional[str]) -> None:
    """Initializes a GRR Hunt Osquery collector.

    Args:
      reason (str): justification for GRR access.
      timeout_millis (int): Osquery timeout in milliseconds
      ignore_stderr_errors (bool): Ignore osquery stderr errors
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
    self.GrrSetUp(
        reason, grr_server_url, grr_username, grr_password, approvers=approvers,
        verify=verify, message_callback=self.PublishMessage)

    self.HuntSetup(match_mode, client_operating_systems, client_labels)

    self.timeout_millis = timeout_millis
    self.ignore_stderr_errors = ignore_stderr_errors

  def Process(self) -> None:
    """Starts a new Osquery GRR hunt."""
    osquery_containers = self.GetContainers(containers.OsqueryQuery)

    for osquery_container in osquery_containers:
      hunt_args = osquery_flows.OsqueryFlowArgs()
      hunt_args.query = osquery_container.query
      hunt_args.timeout_millis = self.timeout_millis
      hunt_args.ignore_stderr_errors = self.ignore_stderr_errors

      self._CreateAndStartHunt('OsqueryFlow', hunt_args)

class GRRHuntYaraScanner(GRRHunt):
  """Yara collector for a GRR Hunt.

  Attributes:
    timeout_millis (int): the number of milliseconds before osquery timeouts.
    ignore_stderr_errors (bool): ignore stderr errors from osquery.
  """

  DEFAULT_OSQUERY_TIMEOUT_MILLIS = 300000

  YARA_MODULES = {
    "hash.": "import \"hash\"",
    "pe.": "import \"pe\"",
    "elf.": "import \"elf\"",
    "math.": "import \"math\"",
  }

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
    super().__init__(state, name=name, critical=critical)
    self.process_ignorelist_regex = ''

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            reason: str,
            hunt_description: str,
            grr_server_url: str,
            grr_username: str,
            grr_password: str,
            approvers: str,
            verify: bool,
            match_mode: Optional[str],
            client_operating_systems: Optional[str],
            client_labels: Optional[str],
            client_limit: str,
            process_ignorelist: Union[List[str], str],
            ) -> None:
    """Initializes a GRR Hunt Osquery collector.

    Args:
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_username: GRR username.
      grr_password: GRR password.
      approvers: comma-separated GRR approval recipients.
      verify (bool): True to indicate GRR server's x509 certificate
          should be verified.
      match_mode: match mode of the client rule set.
          (all/ALL or any/ANY).
      client_operating_systems: a comma separated list of
          client OS types (win, osx or linux).
      client_labels: a comma separated list of client labels.
      client_limit: The number of clients to run the hunt on. 0 for no limit.
      process_ignorelist: A list of strings process executable paths to ignore.
          Can also be passed in one string as a comma-separated list processes.
    """
    self.GrrSetUp(
        reason, grr_server_url, grr_username, grr_password, approvers=approvers,
        verify=verify, message_callback=self.PublishMessage)

    if isinstance(process_ignorelist, list):
      joined = "|".join(process_ignorelist)
    elif isinstance(process_ignorelist, str):
      joined = process_ignorelist

    self.process_ignorelist_regex = r"(?i)^(?!" + joined + r").*"
    if not re.compile(self.process_ignorelist_regex):
      self.ModuleError('Invalid regex for process_ignorelist', critical=True)

    extra_hunt_runner_args: Dict[str, Union[str, int]] = {
        'client_limit': int(client_limit),
        'client_rate': 1000,
        'crash_limit': 1000,
        'per_client_cpu_limit': 2000,
        'avg_cpu_seconds_per_client_limit': 2000,
        'network_bytes_limit': 10*1024*1024*1024,
    }

    self.hunt_description = hunt_description

    self.HuntSetup(
        match_mode,
        client_operating_systems,
        client_labels,
        extra_hunt_runner_args=extra_hunt_runner_args)

  def Process(self) -> None:
    """Starts a new Osquery GRR hunt."""
    yara_containers = self.GetContainers(containers.YaraRule)

    selected_headers = set()
    for rule in yara_containers:
      for prefix, header in self.YARA_MODULES.items():
        condition = rule.rule_text.split("condition:")[1]
        if prefix in condition:
          selected_headers.add(header)

    concatenated_rules = "\n\n".join(
        [container.rule_text for container in yara_containers])

    final_rule_text = ("\n".join(sorted(selected_headers)) +
                      "\n\n" + concatenated_rules)

    flow_args = grr_flows.YaraProcessScanRequest(
      yara_signature=final_rule_text,
      ignore_grr_process=True,
      process_regex=self.process_ignorelist_regex,
      dump_process_on_match=True,
      process_dump_size_limit= 256 * 1024 * 1024,
    )

    self._CreateAndStartHunt('YaraProcessScan', flow_args)



class GRRHuntDownloaderBase(GRRHunt):
  """Base class for modules that download results from a GRR Hunt.

  Attributes:
    reason (str): justification for GRR access.
    approvers (str): comma-separated GRR approval recipients.
    hunt_id (str): the GRR Hunt Id.
    output_path (str): the path to store GRR Hunt results.
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
    super(GRRHuntDownloaderBase, self).__init__(
        state, name=name, critical=critical)
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
        reason, grr_server_url, grr_username, grr_password, approvers=approvers,
        verify=verify, message_callback=self.PublishMessage)
    self.hunt_id = hunt_id
    self.output_path = tempfile.mkdtemp()

  def _CollectHuntResults(self, hunt: Hunt) -> List[Tuple[str, str]]:
    """Downloads the hunt results.

    To be implemented by concrete subclasses. Requests to the GRR Api should be
    wrapped with the _WrapGRRRequestWithApproval() function.

    Args:
      hunt (object): GRR hunt object to download from.

    Returns:
      list[tuple[str, str]]: a list of pairs that are composed of human-readable
          description of the collection source, for example the name of the
          source host, and the path to the collected data.

    Raises:
      NotImplementedError as this class should not be used directly.
    """
    raise NotImplementedError

  def Process(self) -> None:
    """Downloads the results of a GRR hunt.

    Raises:
      RuntimeError: if no items specified for collection.
    """
    hunt = self.grr_api.Hunt(self.hunt_id).Get()

    for description, path in self._CollectHuntResults(hunt):
      container = containers.File(name=description, path=path)
      self.StoreContainer(container)


class GRRHuntDownloader(GRRHuntDownloaderBase):
  """Downloads a file archive from a GRR hunt.

  Attributes:
    reason (str): justification for GRR access.
    approvers (str): comma-separated GRR approval recipients.
    hunt_id (str): the GRR Hunt Id.
    output_path (str): the path to store GRR Hunt results.
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
    super(GRRHuntDownloader, self).__init__(
        state, name=name, critical=critical)

  # TODO: change object to more specific GRR type information.
  def _CollectHuntResults(self, hunt: Hunt) -> List[Tuple[str, str]]:
    """Downloads the current set of files in results.

    Args:
      hunt (object): GRR hunt object to download files from.

    Returns:
      list[tuple[str, str]]: a list of pairs that are composed of human-readable
          description of the collection source, for example the name of the
          source host, and the path to the collected data.

    Raises:
      DFTimewolfError: if approval is needed and approvers were not specified.
    """
    if not os.path.isdir(self.output_path):
      os.makedirs(self.output_path)

    output_file_path = os.path.join(
        self.output_path, '.'.join((self.hunt_id, 'zip')))

    if os.path.exists(output_file_path):
      self.logger.info(
          f'{output_file_path:s} already exists: Skipping')
      return []

    try:
      self._WrapGRRRequestWithApproval(
          hunt, self._GetAndWriteArchive, self.logger, hunt, output_file_path)
    except DFTimewolfError as exception:
      self.ModuleError(exception.message, critical=exception.critical)

    results = self._ExtractHuntResults(output_file_path)
    self.PublishMessage(
        f'Wrote results of {hunt.hunt_id} to {output_file_path}')
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
              self.logger.warning(f'Extraction error: {exception:s}')
              return []

    except OSError as exception:
      msg = f'Error manipulating file {output_file_path:s}: {exception!s}'
      self.ModuleError(msg, critical=True)
    except zipfile.BadZipfile as exception:
      msg = f'Bad zipfile {output_file_path:s}: {exception!s}'
      self.ModuleError(msg, critical=True)

    try:
      os.remove(output_file_path)
    except OSError as exception:
      self.logger.warning(
          f'Output path {output_file_path:s} '
          f'could not be removed: {exception:s}')

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


class GRRHuntOsqueryDownloader(GRRHuntDownloaderBase):
  """Downloads osquery results from a GRR hunt.

  Attributes:
    reason (str): justification for GRR access.
    approvers (str): comma-separated GRR approval recipients.
    hunt_id (str): the GRR Hunt Id.
    output_path (str): the path to store GRR Hunt results.
    results (List[Tuple[str, str]]): a list of results represented as a tuple,
        comprising the hostname and the file path to the corresponding
        results.
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
    super(GRRHuntOsqueryDownloader, self).__init__(
        state, name=name, critical=critical)
    self.results: List[Tuple[str, str]] = []

  def _CollectHuntResults(self, hunt: Hunt) -> List[Tuple[str, str]]:
    """Downloads the current set of results.

    Args:
      hunt (object): GRR hunt object to download results from.

    Returns:
      list[tuple[str, str]]: a list of pairs that are composed of human-readable
          description of the collection source, for example the name of the
          source host, and the path to the collected data.

    Raises:
      DFTimewolfError: if approval is needed and approvers were not specified.
    """
    try:
      self._WrapGRRRequestWithApproval(
          hunt, self._GetAndWriteResults, self.logger, hunt, self.output_path)
    except DFTimewolfError as exception:
      self.ModuleError(exception.message, critical=exception.critical)

    self.PublishMessage(
        f'Wrote results of {hunt.hunt_id} to {self.output_path}')
    return self.results

  def _GetAndWriteResults(
      self, hunt: Hunt, output_path: str) -> List[Tuple[str, str]]:
    """Retrieves and writes hunt results.

    Function is necessary for the _WrapGRRRequestWithApproval to work.

    Args:
      hunt: GRR hunt object.
      output_path: output path where to write the GRR Hunt results.

    Returns:
      list[tuple[str, str]]: a list of pairs of a human-readable description of
          the source of the collection, for example the name of the source host,
          and the path to the collected data.
    """
    for result in hunt.ListResults():
      payload = result.payload

      grr_client = list(self.grr_api.SearchClients(result.client.client_id))[0]
      client_hostname = grr_client.data.os_info.fqdn.lower()

      if not isinstance(payload, osquery_flows.OsqueryResult):
        self.ModuleError(
            f'Incorrect results format from {result.client.client_id} '
            f'({client_hostname}).  Possibly not an osquery hunt.',
            critical=True)
        continue

      headers = [column.name for column in payload.table.header.columns]
      data = [row.values for row in payload.table.rows]
      data_frame = pd.DataFrame.from_records(data, columns=headers)

      output_filename = os.path.join(output_path, f'{client_hostname}.csv')
      data_frame.to_csv(output_filename)
      self.results.append((client_hostname, output_filename))

    return self.results


modules_manager.ModulesManager.RegisterModules([
    GRRHuntArtifactCollector,
    GRRHuntFileCollector,
    GRRHuntOsqueryCollector,
    GRRHuntYaraScanner,
    GRRHuntDownloader,
    GRRHuntOsqueryDownloader])
