# -*- coding: utf-8 -*-
"""Processes GCP cloud disks using Turbinia.
Threaded version of existing Turbinia module."""

import getpass
import os
import tempfile
import time
from typing import Dict, List, Optional, TYPE_CHECKING, Tuple, Any, Union, Type

# We import a class to avoid importing the whole turbinia module.
from turbinia import TurbiniaException
from turbinia import client as turbinia_client
from turbinia import config as turbinia_config
from turbinia import evidence, output_manager
from turbinia.message import TurbiniaRequest

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager

if TYPE_CHECKING:
  from dftimewolf.lib import state

# pylint: disable=abstract-method,no-member
class TurbiniaProcessorThreadedBase(module.ThreadAwareModule):
  """Base class for processing with Turbinia. This is a threaded version of an
  equivalent module.

  Attributes:
    turbinia_config_file (str): Full path to the Turbinia config file to use.
    client (TurbiniaClient): Turbinia client.
    instance (str): name of the Turbinia instance
    project (str): name of the GCP project containing the disk to process.
    run_all_jobs (bool): Whether to run all jobs or to remove slow-running jobs:
        'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob', 'PhotorecJob'.
    sketch_id (int): The Timesketch sketch id
    turbinia_region (str): GCP region in which the Turbinia server is running.
    turbinia_zone (str): GCP zone in which the Turbinia server is running.
  """

  def __init__(self,
               state: "state.DFTimewolfState",
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a Turbinia base processor.

    Args:
      state (state.DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(TurbiniaProcessorThreadedBase, self).__init__(
        state, name=name, critical=critical)
    self.turbinia_config_file = ''
    self._output_path = str()
    self.client = None  # type: turbinia_client.BaseTurbiniaClient
    self.instance = None
    self.project = str()
    self.run_all_jobs = False
    self.sketch_id = int()
    self.turbinia_region = None
    self.turbinia_zone = str()

  def _DeterminePaths(
      self,
      task_data: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """Builds lists of local and remote paths from data retured by Turbinia.

    This finds all .plaso, hashes.json, and BinaryExtractorTask files in the
    Turbinia output, and determines if they are local or remote (it's possible
    this will be running against a local instance of Turbinia).

    Args:
      task_data (list[dict]): List of dictionaries representing Turbinia task
          data.

    Returns:
      tuple[list, list]: A tuple of two lists. The first element contains the
          local paths, the second element contains the remote (GS) paths.
    """
    local_paths = []
    gs_paths = []
    for task in task_data:
      # saved_paths may be set to None
      saved_paths = task.get('saved_paths', [])
      for path in saved_paths:

        if path.endswith('.plaso') or \
            path.endswith('BinaryExtractorTask.tar.gz') or \
            path.endswith('hashes.json'):

          if path.startswith('gs://'):
            gs_paths.append(path)
          else:
            local_paths.append(path)

    return local_paths, gs_paths

  def _DownloadFilesFromGCS(self,
                            timeline_label: str,
                            gs_paths: List[str]) -> List[Tuple[str, str]]:
    """Downloads files stored in Google Cloud Storage to the local filesystem.

    Args:
      timeline_label (str): Label to use to construct the path list.
      gs_paths (List[str]):  gs:// URI to files that need to be downloaded
          from GS.

    Returns:
      list[tuple[str, str]]: A List of tuples containing the timeline label for
        this path, and a local path where GS files have been copied to.
    """
    # TODO: Externalize fetching files from GCS buckets to a different module.

    local_paths = []
    for path in gs_paths:
      local_path = None
      try:
        output_writer = output_manager.GCSOutputWriter(
            path, local_output_dir=self._output_path)
        local_path = output_writer.copy_from(path)
      except TurbiniaException as exception:
        # Don't add a critical error for now, until we start raising errors
        # instead of returning manually each
        self.ModuleError(str(exception), critical=False)
      self.logger.success('Downloaded {0:s} to {1:s}'.format(path, local_path))

      if local_path:
        local_paths.append((timeline_label, local_path))

    return local_paths

  def TurbiniaSetUp(self,
                    project: str,
                    turbinia_zone: str,
                    sketch_id: int,
                    run_all_jobs: bool) -> None:
    """Sets up the object attributes.

    Args:
      project (str): name of the GCP project containing the disk to process.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      sketch_id (int): The Timesketch sketch ID.
      run_all_jobs (bool): Whether to run all jobs instead of a faster subset.
    """
    self.project = project
    self.turbinia_zone = turbinia_zone
    self.sketch_id = sketch_id
    self.run_all_jobs = run_all_jobs

    turbinia_config.LoadConfig(config_file=self.turbinia_config_file)
    if not self.project:
      self.project = turbinia_config.TURBINIA_PROJECT
    if not self.turbinia_zone:
      self.turbinia_zone = turbinia_config.TURBINIA_ZONE

    if not self.project or not self.turbinia_zone:
      self.ModuleError(
          'project or turbinia_zone are not all specified, bailing out',
          critical=True)
      return

    self.turbinia_region = turbinia_config.TURBINIA_REGION
    self.instance = turbinia_config.INSTANCE_ID
    if turbinia_config.TURBINIA_PROJECT != self.project:
      self.ModuleError(
          'Specified project {0!s} does not match Turbinia configured '
          'project {1!s}. Use gcp_turbinia_disk_copy_ts recipe to copy the '
          'disk into the same project.'.format(
              self.project, turbinia_config.TURBINIA_PROJECT), critical=True)
      return
    self._output_path = tempfile.mkdtemp()
    self.client = turbinia_client.get_turbinia_client()

  def TurbiniaProcess(
      self, evidence_: evidence.Evidence) -> List[Dict[str, Any]]:
    """Creates and sends a Turbinia processing request.

    Args:
      evidence_(turbinia.evidence.Evidence): The evidence to process

    Returns:
      list[dict]: The Turbinia task data
    """
    try:
      evidence_.validate()
    except TurbiniaException as exception:
      self.ModuleError(str(exception), critical=True)

    request = TurbiniaRequest(requester=getpass.getuser())
    request.evidence.append(evidence_)
    if self.sketch_id:
      request.recipe['globals']['sketch_id'] = self.sketch_id
    if not self.run_all_jobs:
      request.recipe['globals']['jobs_denylist'] = [
          'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob', 'PhotorecJob']

    threatintel = self.state.GetContainers(containers.ThreatIntelligence)
    if threatintel:
      self.logger.info(
          'Sending {0:d} threatintel to Turbinia GrepWorkers...'.format(
              len(threatintel)))
      indicators = [item.indicator for item in threatintel]
      request.recipe['globals']['filter_patterns'] = indicators

    request_dict = {
        'instance': self.instance,
        'project': self.project,
        'region': self.turbinia_region,
        'request_id': request.request_id
    }

    task_data = []  # type: List[Dict[str, str]]
    try:
      self.logger.success(
          'Creating Turbinia request {0:s} with Evidence {1!s}'.format(
              request.request_id, evidence_.name))
      self.client.send_request(request)
      self.logger.info('Waiting for Turbinia request {0:s} to complete'.format(
          request.request_id))

      # Workaround for rate limiting in turbinia when checking task status
      finished = False
      while not finished:
        try:
          self.client.wait_for_request(**request_dict)
          task_data = self.client.get_task_data(**request_dict)

          finished = True
        except RuntimeError as exception:
          if 'Cloud function [gettasks] call failed' not in str(exception) and \
              'RATE_LIMIT_EXCEEDED' not in str(exception):
            raise exception
          self.logger.info('Rate limit for gettasks hit. Pausing 60 seconds.')
          time.sleep(60)
    except TurbiniaException as exception:
      # TODO: determine if exception should be converted into a string as
      # elsewhere in the codebase.
      self.ModuleError(str(exception), critical=True)
      return task_data

    message = self.client.format_task_status(full_report=True, **request_dict)
    short_message = self.client.format_task_status(**request_dict)
    self.logger.info(short_message)
    # Store the message for consumption by any reporting modules.
    report = containers.Report(
        module_name='TurbiniaProcessor',
        text=message,
        text_format='markdown')
    self.state.StoreContainer(report)

    return task_data


class TurbiniaGCPProcessorThreaded(TurbiniaProcessorThreadedBase):
  """Processes Google Cloud (GCP) disks with Turbinia. This is a threaded
  version of an equivalent module."""

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
    super(TurbiniaGCPProcessorThreaded, self).__init__(
        state, name=name, critical=critical)

  # pylint: disable=arguments-differ
  def SetUp(self,
            turbinia_config_file: str,
            disks: str,
            project: str,
            turbinia_zone: str,
            sketch_id: int,
            run_all_jobs: bool) -> None:
    """Sets up the object attributes.

    Args:
      turbinia_config_file (str): Full path to the Turbinia config file to use.
      disks (str): Comma separated list of disk names
      project (str): name of the GCP project containing the disk to process.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      sketch_id (int): The Timesketch sketch ID.
      run_all_jobs (bool): Whether to run all jobs instead of a faster subset.
    """

    self.turbinia_config_file = turbinia_config_file

    if disks is not None:
      for disk in disks.split(','):
        if disk:
          self.state.StoreContainer(containers.GCEDisk(disk))
    try:
      self.TurbiniaSetUp(project, turbinia_zone, sketch_id, run_all_jobs)
    except TurbiniaException as exception:
      self.ModuleError(str(exception), critical=True)
      return

  # pylint: disable=arguments-renamed
  def Process(self, disk_container: containers.GCEDisk) -> None:
    """Process a disk with Turbinia.

    Args:
      disk_container: Container referencing a GCE Disk."""
    log_file_path = os.path.join(self._output_path, 'turbinia-{0:s}.log'\
        .format(disk_container.name))
    print('Turbinia log file: {0:s}'.format(log_file_path))

    evidence_ = evidence.GoogleCloudDisk(
        disk_name=disk_container.name,
        project=self.project,
        zone=self.turbinia_zone)

    task_data = self.TurbiniaProcess(evidence_)

    local_paths, gs_paths = self._DeterminePaths(task_data)

    if not local_paths and not gs_paths:
      self.logger.warning('No interesting files found in Turbinia output.')

    timeline_label = '{0:s}-{1:s}'.format(self.project, disk_container.name)
    # Any local files that exist we can add immediately to the output
    all_local_paths = [
        (timeline_label, p) for p in local_paths if os.path.exists(p)]

    downloaded_gs_paths = self._DownloadFilesFromGCS(timeline_label, gs_paths)
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

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.GCEDisk

  def GetThreadPoolSize(self) -> int:
    return 5

  def PreSetUp(self) -> None:
    pass

  def PostSetUp(self) -> None:
    pass

  def PreProcess(self) -> None:
    pass

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(TurbiniaGCPProcessorThreaded)
