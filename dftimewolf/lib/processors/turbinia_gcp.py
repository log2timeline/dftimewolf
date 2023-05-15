"""Processes GCP cloud disks using Turbinia."""

import os
from typing import Any, Dict, Optional, TYPE_CHECKING, Type, Union, Set

import magic

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.processors.turbinia_base import TurbiniaProcessorBase

if TYPE_CHECKING:
  from dftimewolf.lib import state


class TurbiniaGCPProcessor(TurbiniaProcessorBase, module.ThreadAwareModule):
  """Processes Google Cloud (GCP) disks with Turbinia.

  Attributes:
    request_ids Set[str]: Turbinia requests for jobs being processed.
  """

  def __init__(
      self,
      state: "state.DFTimewolfState",
      name: Optional[str] = None,
      critical: bool = False) -> None:
    """Initializes a Turbinia Google Cloud (GCP) disks processor.

    Args:
      state (state.DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    module.ThreadAwareModule.__init__(self, state, name=name, critical=critical)
    TurbiniaProcessorBase.__init__(
        self, state, self.logger, name=name, critical=critical)
    self.request_ids = set()

  def _BuildContainer(
      self, path: str, description: str
  ) -> Union[containers.File, containers.ThreatIntelligence]:
    """Builds a container from a path."""
    container: Union[containers.File, containers.ThreatIntelligence]
    if path.endswith('BinaryExtractorTask.tar.gz'):
      self.PublishMessage(f'Found BinaryExtractorTask result: {path}')
      container = containers.ThreatIntelligence(
          name='BinaryExtractorResults', indicator=None, path=path)
    elif path.endswith('hashes.json'):
      self.PublishMessage(f'Found hashes.json: {path}')
      container = containers.ThreatIntelligence(
          name='ImageExportHashes', indicator=None, path=path)
    elif path.endswith('.plaso'):
      self.PublishMessage(f'Found plaso result: {path}')
      container = containers.File(name=description, path=path)
    elif magic.from_file(path, mime=True).startswith('text'):
      self.PublishMessage(f'Found result: {path}')
      container = containers.File(name=description, path=path)
    else:
      self.PublishMessage(
          f'Skipping result of type {magic.from_file(path)} at: {path}')

    return container

  def _CreateTurbiniaRequest(
      self, request_container: containers.TurbiniaRequest):
    """Creates a new Turbinia request.

    Args:
      request_container (containers.TurbiniaRequest): Turbinia request.
    """
    evidence = {
        'type': 'GoogleCloudDisk',
        'disk_name': request_container.evidence_name,
        'project': self.project,
        'zone': self.turbinia_zone
    }
    threat_intel_indicators = None
    threatintel = self.GetContainers(containers.ThreatIntelligence)
    if threatintel:
      self.logger.info(
          f'Sending {len(threatintel)} threatintel to Turbinia GrepWorkers...')
      threat_intel_indicators = [item.indicator for item in threatintel]

    yara_rules = None
    yara_containers = self.GetContainers(containers.YaraRule)
    if yara_containers:
      self.logger.info(
          f'Sending {len(yara_containers)} Yara rules to Turbinia '
          'Plaso worker...')
      yara_rules = [rule.rule_text for rule in yara_containers]

    request_id = self.TurbiniaStart(
        evidence, threat_intel_indicators, yara_rules)
    if not request_id:
      self.ModuleError('Turbinia request failed', critical=True)

    return request_id

  # pylint: disable=arguments-differ
  def SetUp(
      self,
      project: str,
      turbinia_auth: bool,
      turbinia_recipe: Union[str, None],
      turbinia_zone: str,
      turbinia_api: str,
      incident_id: str,
      sketch_id: int,
      request_ids: Set[str] = set(),
      disk_names: str = '') -> None:
    """Sets up the object attributes.

    Args:
      disk_names (str): names of the disks to process.
      project (str): name of the GCP project containing the disk to process.
      turbinia_auth (bool): Turbinia auth flag.
      turbinia_api (str): Turbinia API endpoint.
      turbinia_recipe (str): Turbinia recipe name.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      incident_id (str): The incident ID.
      sketch_id (int): The sketch ID.
      request_ids Set[str]: Turbinia requests for jobs being processed.
      disk_names (str): names of the disks to process.
    """

    if (disk_names and request_ids) or (not disk_names and not request_ids):
      self.ModuleError(
          'One of disk_names or request_ids must be specified, but not both.',
          critical=True)
      return

    if request_ids:
      self.request_ids = {
          request_ids.strip()
          for request_ids in request_ids.split(',')
          if request_ids.strip()
      }
      for request_id in self.request_ids:
        self.StoreContainer(
            containers.TurbiniaRequest(project=project, request_id=request_id))

    if disk_names:
      for disk in disk_names.strip().split(','):
        if not disk:
          continue
        self.StoreContainer(
            containers.TurbiniaRequest(project=project, evidence_name=disk))
        #self.StoreContainer(containers.GCEDisk(name=disk, project=project))

    self.TurbiniaSetUp(
        project, turbinia_auth, turbinia_recipe, turbinia_zone, turbinia_api,
        incident_id, sketch_id)

  def PreProcess(self) -> None:
    """Ensure ForensicsVM containers from previous modules are processed.

    Before the addition of containers.GCEDiskEvidence, containers.ForensicsVM
    was used to track disks needing processing by Turbinia via this module. Here
    we grab those containers and track the disks for processing by this module,
    for any modules that aren't using the new container yet.
    """
    vm_containers = self.GetContainers(containers.ForensicsVM)
    for container in vm_containers:
      if container.evidence_disk and container.evidence_disk.name:
        self.StoreContainer(
            containers.GCEDisk(
                name=container.evidence_disk.name, project=self.project))
    self.state.DedupeContainers(containers.GCEDisk)

  # pylint: disable=arguments-renamed
  def Process(self, request_container: containers.TurbiniaRequest) -> None:
    """Process a GCE Disk with Turbinia."""
    request_id = ''
    task: Dict[str, Any] = {}
    report = ''

    if request_container.project != self.project:
      self.logger.info(
          f'Found disk "{request_container.name}" but skipping as it '
          f'is in a different project "{request_container.project}".')
      return

    if request_container.request_id:
      # We have a request ID, so we can skip creating a new Turbinia request.
      request_id = request_container.request_id
      description = request_container.evidence_name
    else:
      # We don't have a request ID, so we need to create a new Turbinia request.
      description = f'{self.project}-{request_container.evidence_name}'
      request_id = self._CreateTurbiniaRequest(request_container)

    self.PublishMessage(f'Turbinia request ID: {request_id}')

    for task, path in self.TurbiniaWait(request_id):
      task_id = task.get('id')
      if not description:
        description = f'{self.project}-{task.get("name")}'
      self.PublishMessage(f'New output file {path} found for task {task_id}')
      path = self._DownloadFilesFromAPI(task, path)
      if not path:
        self.logger.warning(
            f'No interesting output files could be found for task {task_id}')
        continue
      self.PublishMessage(f'Downloaded file {path} for task {task_id}')
      container = self._BuildContainer(path, description)
      self.PublishMessage(f'Streaming container: {container.path}')
      self.StreamContainer(container)

    # Generate a Turbinia report and store it in the state.
    report = self.TurbiniaFinishReport(request_id)
    self.StoreContainer(
        containers.Report(
            module_name='TurbiniaProcessor',
            text=report,
            text_format='markdown'))
    self.PublishMessage(report)

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.TurbiniaRequest

  def GetThreadPoolSize(self) -> int:
    return self.parallel_count

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(TurbiniaGCPProcessor)
