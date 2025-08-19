# -*- coding: utf-8 -*-
"""Export disk image from a GCP project to Google Cloud Storage."""


from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics import errors as lcf_errors

from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState
from dftimewolf.lib.exporters.gce_disk_export_base import GoogleCloudDiskExportBase  # pylint: disable=line-too-long


# pylint: disable=line-too-long


class GoogleCloudDiskExport(GoogleCloudDiskExportBase):
  """Google Cloud Platform (GCP) Disk Export.

  This module copies a GCE Disk into GCS storage.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: str | None=None,
               critical: bool=False) -> None:
    """Initializes a Google Cloud Platform (GCP) Disk Export.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super().__init__(state, name=name, critical=critical)
    self._source_project: gcp_project.GoogleCloudProject = None
    self._analysis_project: gcp_project.GoogleCloudProject = None
    self._gcs_output_location: str = None
    self._image_format: str = None
    self._exported_image_name: str = None

  def SetUp(self,
            source_project_name: str,
            gcs_output_location: str,
            analysis_project_name: str,
            source_disk_names: str,
            remote_instance_name: str,
            all_disks: bool,
            exported_image_name: str,
            image_format: str) -> None:
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
    """
    self._image_format = image_format
    self._gcs_output_location = gcs_output_location
    self._exported_image_name = exported_image_name

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
        container.metadata['SOURCE_MACHINE'] = self.remote_instance_name
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

      image_object = self._analysis_project.compute.CreateImageFromDisk(
          self._source_project.compute.GetDisk(source_disk.name))
      # If self.exported_image_name = None, default output_name is
      # {src_disk.name}-{TIMESTAMP('%Y%m%d%H%M%S')}.tar.gz
      output_url = image_object.ExportImage(self._gcs_output_location,
                                            output_name=self._exported_image_name,
                                            image_format=self._image_format)
      image_object.Delete()
      self.logger.info(f'Disk was exported to: {output_url}')
      container = containers.GCSObject(path=output_url)
      container.metadata.update(source_disk.metadata)
      self.StoreContainer(container)


modules_manager.ModulesManager.RegisterModule(GoogleCloudDiskExport)
