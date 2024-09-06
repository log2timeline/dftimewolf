# -*- coding: utf-8 -*-
"""Processes a directory of artifacts with Turbinia."""

import tempfile

from typing import Optional, TYPE_CHECKING, Type
from pathlib import Path

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.processors.turbinia_base import TurbiniaProcessorBase

if TYPE_CHECKING:
  from dftimewolf.lib import state


# pylint: disable=no-member
class TurbiniaArtifactProcessor(TurbiniaProcessorBase,
                                module.ThreadAwareModule):
  """Processes Exported GRR Artifacts with Turbinia.

  Attributes:
    directory_path (str): Name of the directory to process.
  """

  def __init__(
      self,
      state: "state.DFTimewolfState",
      name: Optional[str] = None,
      critical: bool = False) -> None:
    """Initializes a Turbinia Artifacts disks processor.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    module.ThreadAwareModule.__init__(self, state, name=name, critical=critical)
    TurbiniaProcessorBase.__init__(
        self, state, self.logger, name=name, critical=critical)
    self.output_directory = ''

  # pylint: disable=arguments-differ
  def SetUp(
      self, project: str, turbinia_recipe: Optional[str],
      turbinia_zone: str, turbinia_api: str, output_directory: str,
      incident_id: str, sketch_id: str, priority_filter: int = 100, 
      turbinia_auth: bool = False) -> None:
    """Sets up the object attributes.

    Args:
      project (str): name of the GCP project containing the disk to process.
      turbinia_auth (bool): Turbinia auth flag.
      turbinia_recipe (str): Turbinia recipe name.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      output_directory (str): Name of the directory to process.
      sketch_id (str): The Timesketch sketch ID.
    """
    self.output_directory = output_directory
    if not self.output_directory:
      self.output_directory = tempfile.mkdtemp(prefix='turbinia-results')
      self.PublishMessage(
          f'Turbinia results will be dumped to {self.output_directory}')

    self.TurbiniaSetUp(
        project,
        turbinia_recipe,
        turbinia_zone,
        turbinia_api,
        incident_id,
        int(sketch_id) if sketch_id else 0,
        priority_filter,
        turbinia_auth)

  # pytype: disable=signature-mismatch
  def Process(self, container: containers.File) -> None:
    # pytype: enable=signature-mismatch
    """Process files with Turbinia."""

    self.logger.info(
      "Processing remote FS path {0:s} from previous collector".format(
        container.path
      )
    )

    # Upload evidence file before starting the Turbinia request
    file_path = self.UploadEvidence(Path(container.path))
    if not file_path:
      self.ModuleError(
        'There was an error uploading the file to Turbinia', critical=True)
    # Send Turbinia request
    evidence = {'type': 'CompressedDirectory', 'source_path': file_path}
    request_id = self.TurbiniaStart(evidence)
    self.PublishMessage(f'Turbinia request ID: {request_id}')

    for task, path in self.TurbiniaWait(request_id):
      # Try to set a descriptive name for the container
      try:
        task_name = task['name']
        task_id = task['id']
        reason = task['reason']
        descriptive_name = f'{task_name}-{task_id}-{reason}'
      except KeyError as exception:
        self.logger.debug(
          f'Failed to get task key: {str(exception)}, using path for '
          f'cotnainer name instead.')
        descriptive_name = container.path
      # We're only interested in plaso files for the time being.
      if path.endswith('.plaso'):
        local_path = self.DownloadFilesFromAPI(task, path)
        if not local_path:
          self.logger.warning(
              f'No interesting output files could be found for task {task_id}')
          continue
        self.logger.info(f'Found plaso result for task {task["id"]}: {path}')
        fs_container = containers.File(path=local_path, name=descriptive_name)
        self.StreamContainer(fs_container)


  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.File

  def GetThreadPoolSize(self) -> int:
    return self.parallel_count

  @staticmethod
  def KeepThreadedContainersInState() -> bool:
    return False

  def PreProcess(self) -> None:
    pass

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(TurbiniaArtifactProcessor)
