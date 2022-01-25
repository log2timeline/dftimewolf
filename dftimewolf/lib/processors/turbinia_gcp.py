# -*- coding: utf-8 -*-
"""Processes GCP cloud disks using Turbinia."""

import os
from typing import Dict, List, Optional, TYPE_CHECKING, Any, Type, Union

from turbinia import TurbiniaException
from turbinia import config as turbinia_config  #pylint: disable=unused-import
from turbinia import evidence

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

  def __init__(self,
               state: "state.DFTimewolfState",
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a Turbinia Google Cloud (GCP) disks processor.

    Args:
      state (state.DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    module.ThreadAwareModule.__init__(self, state, name=name, critical=critical)
    TurbiniaProcessorBase.__init__(self, self.logger)

  # pylint: disable=arguments-differ
  def SetUp(self,
            turbinia_config_file: str,
            project: str,
            turbinia_zone: str,
            sketch_id: int,
            run_all_jobs: bool,
            disk_names: str = '') -> None:
    """Sets up the object attributes.

    Args:
      turbinia_config_file (str): Full path to the Turbinia config file to use.
      disk_names (str): names of the disks to process.
      project (str): name of the GCP project containing the disk to process.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      sketch_id (int): The Timesketch sketch ID.
      run_all_jobs (bool): Whether to run all jobs instead of a faster subset.
    """
    self.turbinia_config_file = turbinia_config_file

    if disk_names:
      for disk in disk_names.strip().split(','):
        if disk:
          self.state.StoreContainer(containers.GCEDisk(name=disk))

    try:
      self.TurbiniaSetUp(project, turbinia_zone, sketch_id, run_all_jobs)
    except TurbiniaException as exception:
      self.ModuleError(str(exception), critical=True)
      return

  def PreProcess(self) -> None:
    """Ensure ForensicsVM containers from previous modules are processed.

    Before the addition of containers.GCEDisk, containers.ForensicsVM was used
    to track disks needing processing by Turbinia via this module. Here we grab
    those containers and track the disks for processing by this module, for any
    modules that aren't using the new container yet.
    """
    vm_containers = self.state.GetContainers(containers.ForensicsVM)
    for container in vm_containers:
      if container.evidence_disk.name:
        self.state.StoreContainer(
            containers.GCEDisk(name=container.evidence_disk.name))

  # pylint: disable=arguments-renamed
  def Process(self, disk_container: containers.GCEDisk) -> None:
    """Process a GCE Disk with Turbinia."""
    log_file_path = os.path.join(self._output_path, '{0:s}-turbinia.log'.format(
      disk_container.name))

    self.logger.info('Turbinia log file: {0:s}'.format(log_file_path))
    self.logger.info('Using disk {0:s} from previous collector'.format(
        disk_container.name))

    evidence_ = evidence.GoogleCloudDisk(
        disk_name=disk_container.name,
        project=self.project,
        zone=self.turbinia_zone)

    threat_intel_indicators = None
    threatintel = self.state.GetContainers(containers.ThreatIntelligence)
    if threatintel:
      self.logger.info(
          'Sending {0:d} threatintel to Turbinia GrepWorkers...'.format(
              len(threatintel)))
      threat_intel_indicators = [item.indicator for item in threatintel]

    yara_rules = None
    yara_containers = self.state.GetContainers(containers.YaraRule)
    if yara_containers:
      self.logger.info(
          'Sending {0:d} Yara rules to Turbinia Plaso worker...'.format(
              len(yara_containers)))
      yara_rules = [rule.rule_text for rule in yara_containers]

    try:
      task_data, report = self.TurbiniaProcess(
          evidence_, threat_intel_indicators, yara_rules)
    except TurbiniaException as exception:
      self.ModuleError(str(exception), critical=True)

    self.state.StoreContainer(containers.Report(
        module_name='TurbiniaProcessor', text=report, text_format='markdown'))

    local_paths, gs_paths = self._DeterminePaths(task_data)

    if not local_paths and not gs_paths:
      self.ModuleError(
          'No interesting files found in Turbinia output.', critical=True)

    timeline_label = '{0:s}-{1:s}'.format(self.project, disk_container.name)
    # Any local files that exist we can add immediately to the output
    all_local_paths = [
        (timeline_label, p) for p in local_paths if os.path.exists(p)]

    try:
      downloaded_gs_paths = self._DownloadFilesFromGCS(timeline_label, gs_paths)
    except TurbiniaException as exception:
      # Don't add a critical error for now, until we start raising errors
      # instead of returning manually each
      self.ModuleError(str(exception), critical=False)

    all_local_paths.extend(downloaded_gs_paths)
    self.logger.info('Collected {0:d} results'.format(len(all_local_paths)))

    if not all_local_paths:
      self.ModuleError('No interesting files could be found.', critical=True)

    container: Union[containers.File, containers.ThreatIntelligence]
    for description, path in all_local_paths:
      if path.endswith('BinaryExtractorTask.tar.gz'):
        self.logger.success(
            'Found BinaryExtractorTask result: {0:s}'.format(path))
        container = containers.ThreatIntelligence(
            name='BinaryExtractorResults', indicator=None, path=path)
      if path.endswith('hashes.json'):
        self.logger.success('Found hashes.json: {0:s}'.format(path))
        container = containers.ThreatIntelligence(
            name='ImageExportHashes', indicator=None, path=path)
      if path.endswith('.plaso'):
        self.logger.success('Found plaso result: {0:s}'.format(path))
        container = containers.File(name=description, path=path)
      self.state.StoreContainer(container)
  # pylint: enable=arguments-renamed

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.GCEDisk

  def GetThreadPoolSize(self) -> int:
    return self.parallel_count

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(TurbiniaGCPProcessor)
