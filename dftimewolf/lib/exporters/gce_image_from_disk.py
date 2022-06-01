# -*- coding: utf-8 -*-
"""Create disks in GCE from disk images."""

import datetime

from typing import Any, Optional, Type, Union

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeDisk
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class GCEImageFromDisk(module.ThreadAwareModule):
  """Create images in GCE from disks."""

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initialises creating disks in GCE from disk images.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GCEImageFromDisk, self).__init__(
        state, name=name, critical=critical)
    self.source_project: str = ''
    self.source_zone: str = ''
    self.dest_project: str = ''
    self.dest_zone: str = ''

  # pylint: disable=arguments-differ
  def SetUp(self,
      source_disks: Union[str, None],
      source_project: str,
      source_zone: str,
      destination_project: str,
      destination_zone: str,
      name_prefix: str) -> None:
    """SetUp for creating disks in GCE from images.

    GCE Images to use are sourced from either the state, or passed in here.
    Args:
      source_disks: Comma separated list of disk names.
      source_project: The source project of the disks.
      source_zone: The source zone of the disks.
      destination_project: The project in which to create the images.
      destination_zone: The zone in which to create the images.
      name_prefix: An optional prefix for the final image name.
    """
    self.source_project = source_project
    self.source_zone = source_zone
    self.dest_zone = (destination_zone if destination_zone else source_zone)
    self.dest_project = (destination_project if destination_project
        else source_project)
    self.name_prefix = name_prefix

    if source_disks:
      for obj in source_disks.split(','):
        if obj:
          self.state.StoreContainer(containers.GCEDisk(obj, source_project))

  def Process(self, container: containers.GCEDisk) -> None:
    """Creates a GCE disk from an image.

    Args:
      container (containers.GCEImage): The container to process.
    """
    # GCEDisk containers may come from other modules for other projects. Check
    # we only are operating on the intended project.
    if container.project != self.source_project:
      self.logger.info(
          f'Skipping "{container.name}" due to source project mismatch')
      return

    self.logger.info(f'Creating image from disk {container.name}')

    source_disk = GoogleComputeDisk(self.source_project,
                                    self.source_zone,
                                    container.name)

    # We must create a project object for each thread, rather than create and
    # use a class member due to an underlying thread safety issue in
    # httplib2: https://github.com/googleapis/google-cloud-python/issues/3501
    project = gcp_project.GoogleCloudProject(self.dest_project)
    image_name = f'{self.name_prefix}-{source_disk.name}'
    image = project.compute.CreateImageFromDisk(source_disk, name=image_name)
    self.state.StoreContainer(
        containers.GCEImage(image.name, self.dest_project))

    self.logger.info(
        f'Image {image.name} from {container.name} finished creation')

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.GCEDisk

  def GetThreadPoolSize(self) -> int:
    return 10

  def PreProcess(self) -> None:
    pass

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(GCEImageFromDisk)
