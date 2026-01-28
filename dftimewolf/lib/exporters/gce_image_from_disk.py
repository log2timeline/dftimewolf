# -*- coding: utf-8 -*-
"""Create disks in GCE from disk images."""

from typing import Callable, Type, Union

from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeDisk
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import cache
from dftimewolf.lib import telemetry
from dftimewolf.lib.containers import manager as container_manager


class GCEImageFromDisk(module.ThreadAwareModule):
  """Create images in GCE from disks."""

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initialises creating disks in GCE from disk images.

    Args:
      name: The modules runtime name.
      container_manager_: A common container manager object.
      cache_: A common DFTWCache object.
      telemetry_: A common telemetry collector object.
      publish_message_callback: A callback to send modules messages to.
    """
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)
    self.source_project: str = ''
    self.source_zone: str = ''
    self.dest_project: str = ''
    self.dest_zone: str = ''
    self.name_prefix: str = ''

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
          self.StoreContainer(containers.GCEDisk(obj, source_project))

  def Process(self, container: containers.GCEDisk
              ) -> None:  # pytype: disable=signature-mismatch
    """Creates a GCE disk from an image.

    Args:
      container (containers.GCEImage): The container to process.
    """
    # GCEDisk containers may come from other modules for other projects. Check
    # we only are operating on the intended project.
    if container.project != self.source_project:
      self.logger.debug(
        f'Skipping "{container.name}" due to source project mismatch'
      )
      return

    self.logger.debug(f"Creating image from disk {container.name}")

    source_disk = GoogleComputeDisk(self.source_project,
                                    self.source_zone,
                                    container.name)

    # We must create a project object for each thread, rather than create and
    # use a class member due to an underlying thread safety issue in
    # httplib2: https://github.com/googleapis/google-cloud-python/issues/3501
    project = gcp_project.GoogleCloudProject(self.dest_project)
    image_name = common.GenerateUniqueInstanceName(
        prefix=f'{self.name_prefix}-{source_disk.name}',
        truncate_at=common.COMPUTE_NAME_LIMIT)
    image = project.compute.CreateImageFromDisk(source_disk, name=image_name)
    self.StoreContainer(
        containers.GCEImage(image.name, self.dest_project))

    self.logger.debug(
      f"Image {image.name} from {container.name} finished creation"
    )

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    return containers.GCEDisk

  def GetThreadPoolSize(self) -> int:
    return 10

  def PreProcess(self) -> None:
    pass

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(GCEImageFromDisk)
