# -*- coding: utf-8 -*-
"""Export objects from AWS S3 to a GCP GCS bucket."""

from typing import Any, Optional, Type

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeImage
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


IMAGE_BUILD_ROLE_NAME = 'disk_build_role'

class GCEDiskFromImage(module.ThreadAwareModule):
  """Initialises creating disks in GCE from images in GCS."""

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initialises creating disks in GCE from images in GCS.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GCEDiskFromImage, self).__init__(
        state, name=name, critical=critical)
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
          self.state.StoreContainer(containers.GCEImage(obj))


  def Process(self, container: containers.GCEImage) -> None:
    """Creates a GCE disk from an image."""
    self.logger.info('Creating disk from image {0:s}'.format(container.name))

    image = GoogleComputeImage(
        name=container.name,
        project_id=self.dest_project_name,
        zone=self.dest_zone)

    # We must create a new client for each thread, rather than use the class
    # member self.dest_project due to an underlying thread safety issue in
    # httplib2: https://github.com/googleapis/google-cloud-python/issues/3501
    project = gcp_project.GoogleCloudProject(self.dest_project_name)
    disk = project.compute.CreateDiskFromImage( #GoogleComputeDisk
      src_image = image,
      zone = self.dest_zone)
    self.state.StoreContainer(containers.GCEDisk(disk.name))

    self.logger.info('Disk {0:s} finished creation'.format(disk.name))

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.GCEImage

  def GetThreadPoolSize(self) -> int:
    return 10

  def PreSetUp(self) -> None:
    pass

  def PostSetUp(self) -> None:
    pass

  def PreProcess(self) -> None:
    pass

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(GCEDiskFromImage)
