"""Processes GCP cloud disks using Turbinia."""

import os
from typing import Any, Dict, Optional, TYPE_CHECKING, Type, Union

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
    disk_name (str): name of the disk to process.
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
      disk_names (str): names of the disks to process.
    """
    if disk_names:
      for disk in disk_names.strip().split(','):
        if not disk:
          continue
        self.StoreContainer(containers.GCEDisk(name=disk, project=project))

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
  def Process(self, disk_container: containers.GCEDisk) -> None:
    """Process a GCE Disk with Turbinia."""
    request_id = ''
    task: Dict[str, Any] = {}
    report = ''
    evidence = {
        'type': 'GoogleCloudDisk',
        'disk_name': disk_container.name,
        'project': self.project,
        'zone': self.turbinia_zone
    }
    description = f'{self.project}-{disk_container.name}'
    if disk_container.project != self.project:
      self.logger.info(
          f'Found disk "{disk_container.name}" but skipping as it '
          f'is in a different project "{disk_container.project}".')
      return

    log_file_path = os.path.join(
        self.output_path, f'{disk_container.name}-turbinia.log')
    self.logger.info(f'Turbinia log file: {log_file_path}')
    self.logger.info(
        f'Using disk {disk_container.name} from previous collector')

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

    self.PublishMessage(f'Turbinia request ID: {request_id}')

    for task, path in self.TurbiniaWait(request_id):
      task_id = task.get('id')
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
    return containers.GCEDisk

  def GetThreadPoolSize(self) -> int:
    return self.parallel_count

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(TurbiniaGCPProcessor)
