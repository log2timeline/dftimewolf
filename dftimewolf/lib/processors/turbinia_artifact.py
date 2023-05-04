# -*- coding: utf-8 -*-
"""Processes a directory of artifacts with Turbinia."""

import os
import tempfile

from typing import Optional, TYPE_CHECKING, Type

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
    TurbiniaProcessorBase.__init__(self, self.logger)
    self.output_directory = ''

  # pylint: disable=arguments-differ
  def SetUp(
      self, project: str, turbinia_auth: bool, turbinia_recipe: Optional[str],
      turbinia_zone: str, turbinia_api: str, output_directory: str,
      incident_id: str, sketch_id: int) -> None:
    """Sets up the object attributes.

    Args:
      project (str): name of the GCP project containing the disk to process.
      turbinia_auth (bool): Turbinia auth flag.
      turbinia_recipe (str): Turbinia recipe name.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      output_directory (str): Name of the directory to process.
      sketch_id (int): The Timesketch sketch ID.
    """
    self.output_directory = output_directory
    if not self.output_directory:
      self.output_directory = tempfile.mkdtemp(prefix='turbinia-results')
      self.PublishMessage(
          f'Turbinia results will be dumped to {self.output_directory}')

    self.TurbiniaSetUp(
        project, turbinia_auth, turbinia_recipe, turbinia_zone, turbinia_api,
        incident_id, sketch_id)


  def Process(self, container: containers.RemoteFSPath) -> None:
    """Process files with Turbinia."""

    log_file_path = os.path.join(
        self.output_path, '{0:s}_{1:s}-turbinia.log'.format(
            container.hostname, container.path.replace('/', '_')))
    self.logger.info('Turbinia log file: {0:s}'.format(log_file_path))
    self.logger.info(
        'Processing remote FS path {0:s} from previous collector'.format(
            container.path))

    evidence = {'type': 'CompressedDirectory', 'source_path': container.path}
    request_id = self.TurbiniaStart(evidence)
    self.PublishMessage(f'Turbinia request ID: {request_id}')

    for task, path in self.TurbiniaWait(request_id):
      # We're only interested in plaso files for the time being.
      if path.endswith('.plaso'):
        self.PublishMessage(
          f'Found plaso result for task {task["id"]}: {path}')
        container = containers.RemoteFSPath(
            path=path, hostname=container.hostname)
        self.StreamContainer(container)

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.RemoteFSPath

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
