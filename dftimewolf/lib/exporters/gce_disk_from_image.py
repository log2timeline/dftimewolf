# -*- coding: utf-8 -*-
"""Create disks in GCE from disk images."""

from typing import Callable, Type

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeImage
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import cache
from dftimewolf.lib import telemetry
from dftimewolf.lib.containers import manager as container_manager


class GCEDiskFromImage(module.ThreadAwareModule):
  """Create disks in GCE from disk images."""

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
    self.dest_project_name: str = ''
    self.dest_zone: str = ''

  # pylint: disable=arguments-differ
  def SetUp(self,
      dest_project: str,
      dest_zone: str,
      source_images: str = '') -> None:
    """SetUp for creating disks in GCE from images.

    GCE Images to use are sourced from either the state, or passed in here.
    Args:
      dest_project (str): The destination GCP project.
      dest_zone (str): Destination zone for the disks to be created in.
      source_images (str): Comma separated list of images.
    """
    self.dest_project_name = dest_project
    self.dest_zone = dest_zone

    if source_images:
      for obj in source_images.split(','):
        if not obj == "":
          self.StoreContainer(containers.GCEImage(obj, dest_project))


  def Process(self, container: containers.GCEImage
              ) -> None:  # pytype: disable=signature-mismatch
    """Creates a GCE disk from an image.

    Args:
      container (containers.GCEImage): The container to process.
    """
    self.logger.info('Creating disk from image {0:s}'.format(container.name))

    image = GoogleComputeImage(
        name=container.name,
        project_id=self.dest_project_name,
        zone=self.dest_zone)

    # We must create a new client for each thread, rather than use the class
    # member self.dest_project due to an underlying thread safety issue in
    # httplib2: https://github.com/googleapis/google-cloud-python/issues/3501
    project = gcp_project.GoogleCloudProject(self.dest_project_name)
    disk = project.compute.CreateDiskFromImage(
      src_image = image,
      zone = self.dest_zone)
    self.StoreContainer(containers.GCEDisk(
        disk.name,
        self.dest_project_name))

    self.logger.info(f'Disk {disk.name} finished creation')

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    return containers.GCEImage

  def GetThreadPoolSize(self) -> int:
    return 10

  def PreProcess(self) -> None:
    pass

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(GCEDiskFromImage)
