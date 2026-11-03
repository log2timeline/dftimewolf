# -*- coding: utf-8 -*-
"""Export disk image from a GCP project to Google Cloud Storage."""

from typing import Callable

from googleapiclient.errors import HttpError
from libcloudforensics import errors as lcf_errors
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeImage

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import cache
from dftimewolf.lib import spanner_telemetry as telemetry
from dftimewolf.lib.containers import manager as container_manager
from dftimewolf.lib.exporters.gce_disk_export_base import GoogleCloudDiskExportBase  # pylint: disable=line-too-long


# pylint: disable=line-too-long


class GoogleCloudDiskExport(GoogleCloudDiskExportBase):
  """Google Cloud Platform (GCP) Disk Export.

  This module copies a GCE Disk into GCS storage.
  """

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initializes a Google Cloud Platform (GCP) Disk Export.

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

    self._analysis_project: gcp_project.GoogleCloudProject
    self._gcs_output_location: str = ''
    self._image_format: str = ''
    self._exported_image_name: str = ''
    self._cloudbuild_zone: str = ''

  # pylint: disable=arguments-differ
  def SetUp(self,
            source_project_name: str,
            gcs_output_location: str,
            analysis_project_name: str,
            source_disk_names: str,
            remote_instance_name: str,
            all_disks: bool,
            exported_image_name: str,
            image_format: str,
            cloudbuild_zone: str) -> None:
    """Sets up a Google Cloud Platform (GCP) Disk Export.

    This method creates the required objects to initialize
    the GoogleCloudDiskExport class attributes.

    If the analysis_project_name is not specified it will use the
    source_project_name instead.

    If source_disk_names is specified, it will copy the corresponding disks from
    the project, ignoring disks belonging to any specific instances.

    If remote_instance_name is specified, two behaviors are possible:
    * If no other parameters are specified, it will select the instance's boot
      disk
    * if all_disks is set to True, it will select all disks in the project
      that are attached to the instance

    Args:
      source_project_name (str): Source project ID containing
          the disk to export.
      gcs_output_location (str): Google Cloud Storage parent bucket/folder
          path of the exported image.
      analysis_project_name (Optional[str]): Optional. Project ID where the
          disk image is created then exported. If not specified,
          source_project_name will be used.
      source_disk_names (Optional[str]): Optional. Comma separated disk names
          to copy.Default is None.
      remote_instance_name (Optional[str]): Optional. Instance in source
          project to export its disks. Default, if not exist, source_disk_names
          will be used.
      all_disks (Optional[bool]): Optional. True if all disks attached to
          the source instance should be copied. Default is False. If False
          and remote_instance_name is provided it will select the instance's
          boot disk.
      exported_image_name (Optional[str]): Optional. Name of the output file,
          must comply with ^[A-Za-z0-9-]*$' and '.tar.gz' will be appended to
          the name. Default is None, if not exist or if more than one disk
          is selected, exported image name as
          "exported-image-{TIMESTAMP('%Y%m%d%H%M%S')}".
      image_format: The image format to use.
      cloudbuild_zone: The zone in which to launch the cloudbuild job.
    """
    self._image_format = image_format
    self._gcs_output_location = gcs_output_location
    self._exported_image_name = exported_image_name
    self._cloudbuild_zone = cloudbuild_zone or 'us-central1-a'

    self._source_project = gcp_project.GoogleCloudProject(source_project_name)
    if analysis_project_name:
      self._analysis_project = gcp_project.GoogleCloudProject(analysis_project_name)
    else:
      self._analysis_project = self._source_project

    if remote_instance_name:
      instance_disks = self._GetDisksFromInstance(instance_name=remote_instance_name,
                                                  all_disks=all_disks)
      for d in instance_disks:
        container = containers.GCEDisk(name=d.name, project=source_project_name)
        container.metadata['SOURCE_MACHINE'] = self._remote_instance_name
        container.metadata['SOURCE_DISK'] = d.name
        self.StoreContainer(container, for_self_only=True)

    if source_disk_names:
      disk_names = list(filter(None, [d.strip().lower() for d in source_disk_names.split(',') if d]))
      for d in disk_names:
        container = containers.GCEDisk(name=d, project=source_project_name)
        container.metadata['SOURCE_MACHINE'] = 'UNKNOWN_MACHINE'
        container.metadata['SOURCE_DISK'] = d
        self.StoreContainer(container, for_self_only=True)

  def Process(self) -> None:
    """Creates and exports disk image to the output bucket."""
    for source_disk in self.GetContainers(containers.GCEDisk):
      if source_disk.project != self._source_project.project_id:
        self.logger.info('Source project mismatch: skipping %s', str(source_disk))
        continue

      # A resumed run gets the same image name, which also names the exported
      # file, unless exported_image_name is set. Then it reuses the image and
      # the file of an earlier run.
      image_object = GoogleComputeImage(
          self._analysis_project.project_id, '',
          self._ImageName(source_disk.name))
      output_url = self._ExportDisk(source_disk.name, image_object.name)
      self._DeleteImage(image_object)
      self.logger.info(f'Disk was exported to: {output_url}')
      container = containers.GCSObject(path=output_url)
      container.metadata.update(source_disk.metadata)
      self.StoreContainer(container)

  @module.SkipOnResumeIfComplete()
  def _ImageName(self, disk_name: str) -> str:
    """Returns a new name for the image of a disk.

    Args:
      disk_name: The name of the disk.

    Returns:
      The image name.
    """
    return common.GenerateUniqueInstanceName(disk_name, common.COMPUTE_NAME_LIMIT)

  @module.SkipOnResumeIfComplete()
  def _ExportDisk(self, disk_name: str, image_name: str) -> str:
    """Exports a disk to GCS, through an image.

    A crash during the export runs it again, to the same file.

    Args:
      disk_name: The name of the disk.
      image_name: The name of the image to create, or of the image of an
          earlier run.

    Returns:
      The URL of the exported file.
    """
    try:
      self._analysis_project.compute.CreateImageFromDisk(
          self._source_project.compute.GetDisk(disk_name), name=image_name)
    except lcf_errors.ResourceAlreadyExistsError:
      self.logger.info(f'Reusing image {image_name} of an earlier run')

    # If self.exported_image_name is empty, the file name is the image name,
    # with .tar.gz or the image format.
    image_object = GoogleComputeImage(
        self._analysis_project.project_id, '', image_name)
    return image_object.ExportImage(self._gcs_output_location,
                                    output_name=self._exported_image_name,
                                    image_format=self._image_format,
                                    zone=self._cloudbuild_zone)

  def _DeleteImage(self, image: GoogleComputeImage) -> None:
    """Deletes the image of an export. An earlier run may have deleted it."""
    try:
      image.Delete()
    except HttpError as exception:
      if exception.resp.status != 404:
        raise
      self.logger.info(f'Image {image.name} is gone already')


modules_manager.ModulesManager.RegisterModule(GoogleCloudDiskExport)
