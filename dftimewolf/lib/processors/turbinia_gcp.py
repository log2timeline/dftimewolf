# -*- coding: utf-8 -*-
"""Processes GCP cloud disks using Turbinia."""

import getpass
import os
import tempfile

# We import a class to avoid importing the whole turbinia module.
from turbinia import TurbiniaException
from turbinia import client as turbinia_client
from turbinia import config as turbinia_config
from turbinia import evidence, output_manager
from turbinia.message import TurbiniaRequest

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager

# pylint: disable=no-member

# pylint: disable=abstract-method
class TurbiniaProcessorBase(module.BaseModule):
  """Base class for processing with Turbinia.

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

  def __init__(self, state, name=None, critical=False):
    """Initializes a Turbinia base processor.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(TurbiniaProcessorBase, self).__init__(
        state, name=name, critical=critical)
    self.turbinia_config_file = None
    self._output_path = None
    self.client = None
    self.instance = None
    self.project = None
    self.run_all_jobs = None
    self.sketch_id = None
    self.turbinia_region = None
    self.turbinia_zone = None

  def _DeterminePaths(self, task_data):
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
      saved_paths = task.get('saved_paths') or []
      for path in saved_paths:

        if path.endswith('.plaso') or \
            path.endswith('BinaryExtractorTask.tar.gz') or \
            path.endswith('hashes.json'):

          if path.startswith('gs://'):
            gs_paths.append(path)
          else:
            local_paths.append(path)

    return local_paths, gs_paths

  def _DownloadFilesFromGCS(self, timeline_label, gs_paths):
    """Downloads files stored in Google Cloud Storage to the local filesystem.

    Args:
      timeline_label (str): Label to use to construct the path list.
      gs_paths (str):  gs:// URI to files that need to be downloaded from GS.

    Returns:
      list:
        tuple: containing:
          str: The timeline label for this path.
          str: A local path where GS files have been copied to.
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
      self.logger.info('Downloaded {0:s} to {1:s}'.format(path, local_path))

      if local_path:
        local_paths.append((timeline_label, local_path))

    return local_paths

  def TurbiniaSetUp(self, project, turbinia_zone, sketch_id, run_all_jobs):
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

    if self.project is None or self.turbinia_zone is None:
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
    self.client = turbinia_client.TurbiniaClient()

  def TurbiniaProcess(self, evidence_):
    """Creates and sends a Turbinia processing request.

    Args:
      evidence_(turbinia.evidence.Evidence): The evience to proecess

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
      request.recipe['sketch_id'] = self.sketch_id
    if not self.run_all_jobs:
      # TODO(aarontp): Remove once the release with
      # https://github.com/google/turbinia/pull/554 is live.
      request.recipe['jobs_blacklist'] = [
          'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob', 'PhotorecJob']
      request.recipe['jobs_denylist'] = [
          'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob', 'PhotorecJob']

    # Get threat intelligence data from any modules that have stored some.
    # In this case, observables is a list of containers.ThreatIntelligence
    # objects.
    threatintel = self.state.GetContainers(containers.ThreatIntelligence)
    if threatintel:
      self.logger.info(
          'Sending {0:d} threatintel to Turbinia GrepWorkers...'.format(
              len(threatintel)))
      indicators = [item.indicator for item in threatintel]
      request.recipe['filter_patterns'] = indicators

    request_dict = {
        'instance': self.instance,
        'project': self.project,
        'region': self.turbinia_region,
        'request_id': request.request_id
    }

    task_data = None
    try:
      self.logger.info(
          'Creating Turbinia request {0:s} with Evidence {1!s}'.format(
              request.request_id, evidence_.name))
      self.client.send_request(request)
      self.logger.info('Waiting for Turbinia request {0:s} to complete'.format(
          request.request_id))
      self.client.wait_for_request(**request_dict)
      task_data = self.client.get_task_data(**request_dict)
    except TurbiniaException as exception:
      # TODO: determine if exception should be converted into a string as
      # elsewhere in the codebase.
      self.ModuleError(str(exception), critical=True)

    message = self.client.format_task_status(full_report=True, **request_dict)
    short_message = self.client.format_task_status(**request_dict)
    self.logger.info(short_message)

    # Store the message for consumption by any reporting modules.
    report = containers.Report(
        module_name='TurbiniaProcessor', text=message, text_format='markdown')
    self.state.StoreContainer(report)

    return task_data


class TurbiniaGCPProcessor(TurbiniaProcessorBase):
  """Processes Google Cloud (GCP) disks with Turbinia.

  Attributes:
    disk_name (str): name of the disk to process.
  """

  def __init__(self, state, name=None, critical=False):
    """Initializes a Turbinia Google Cloud (GCP) disks processor.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(TurbiniaGCPProcessor, self).__init__(
        state, name=name, critical=critical)
    self.disk_name = None

  # pylint: disable=arguments-differ
  def SetUp(self,
            turbinia_config_file,
            disk_name,
            project,
            turbinia_zone,
            sketch_id,
            run_all_jobs):
    """Sets up the object attributes.

    Args:
      turbinia_config_file (str): Full path to the Turbinia config file to use.
      disk_name (str): name of the disk to process.
      project (str): name of the GCP project containing the disk to process.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      sketch_id (int): The Timesketch sketch ID.
      run_all_jobs (bool): Whether to run all jobs instead of a faster subset.
    """
    # TODO: Consider the case when multiple disks are provided by the previous
    # module or by the CLI.

    self.turbinia_config_file = turbinia_config_file
    self.disk_name = disk_name

    try:
      self.TurbiniaSetUp(project, turbinia_zone, sketch_id, run_all_jobs)
    except TurbiniaException as exception:
      self.ModuleError(str(exception), critical=True)
      return

  def Process(self):
    """Process files with Turbinia."""
    log_file_path = os.path.join(self._output_path, 'turbinia.log')
    print('Turbinia log file: {0:s}'.format(log_file_path))

    vm_containers = self.state.GetContainers(containers.ForensicsVM)
    if vm_containers and not self.disk_name:
      forensics_vm = vm_containers[0]
      self.disk_name = forensics_vm.evidence_disk.name
      self.logger.info(
          'Using disk {0:s} from previous collector'.format(self.disk_name))

    evidence_ = evidence.GoogleCloudDisk(
        disk_name=self.disk_name, project=self.project, zone=self.turbinia_zone)

    task_data = self.TurbiniaProcess(evidence_)

    local_paths, gs_paths = self._DeterminePaths(task_data)

    if not local_paths and not gs_paths:
      self.ModuleError(
          'No interesting files found in Turbinia output.', critical=True)

    timeline_label = '{0:s}-{1:s}'.format(self.project, self.disk_name)
    # Any local files that exist we can add immediately to the output
    all_local_paths = [
        (timeline_label, p) for p in local_paths if os.path.exists(p)]

    downloaded_gs_paths = self._DownloadFilesFromGCS(timeline_label, gs_paths)
    all_local_paths.extend(downloaded_gs_paths)
    self.logger.info('Collected {0:d} results'.format(len(all_local_paths)))

    if not all_local_paths:
      self.ModuleError('No interesting files could be found.', critical=True)

    for description, path in all_local_paths:
      if path.endswith('BinaryExtractorTask.tar.gz'):
        self.logger.info('Found BinaryExtractorTask result: {0:s}'.format(path))
        container = containers.ThreatIntelligence(
            name='BinaryExtractorResults', indicator=None, path=path)
      if path.endswith('hashes.json'):
        self.logger.info('Found hashes.json: {0:s}'.format(path))
        container = containers.ThreatIntelligence(
            name='ImageExportHashes', indicator=None, path=path)
      if path.endswith('.plaso'):
        self.logger.info('Found plaso result: {0:s}'.format(path))
        container = containers.File(name=description, path=path)
      self.state.StoreContainer(container)


modules_manager.ModulesManager.RegisterModule(TurbiniaGCPProcessor)
