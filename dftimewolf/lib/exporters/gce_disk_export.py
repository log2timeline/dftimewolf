# -*- coding: utf-8 -*-
"""Export disk image from a GCP project to Google Cloud Storage."""


import os
from typing import List, Optional

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeDisk

from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState
from dftimewolf.lib.exporters.gce_disk_export_base import GoogleCloudDiskExportBase  # pylint: disable=line-too-long


class GoogleCloudDiskExport(GoogleCloudDiskExportBase):
  """Google Cloud Platform (GCP) Disk Export.

  Attributes:
    source_project (gcp_project.GoogleCloudProject): Source project
        containing the disk/s to export.
    gcs_output_location (str): Google Cloud Storage parent bucket/folder
        path of the exported image.
    analysis_project (gcp_project.GoogleCloudProject): Project where the
        disk image is created then exported.
        If not exit, source_project will be used.
    remote_instance_name (str): Instance that needs forensicating.
    source_disk_names (list[str]): Comma-separated list of disk names to copy.
    all_disks (bool): True if all disks attached to the source
        instance should be copied.
    source_disks (list[gcp_project.compute.GoogleComputeDisk]): List of disks
        to be exported.
    exported_image_name (Optional[str]): Optional. Name of the output file, must
        comply with ^[A-Za-z0-9-]*$' and '.tar.gz' will be appended to the name.
        Default, if not exist or if more than one disk is selected, exported
        image name as "exported-image-{TIMESTAMP('%Y%m%d%H%M%S')}".
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a Google Cloud Platform (GCP) Disk Export.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GoogleCloudDiskExport, self).__init__(
        state, name=name, critical=critical)
    self.source_project = None  # type: gcp_project.GoogleCloudProject
    self.gcs_output_location = str()
    self.analysis_project = None  # type: gcp_project.GoogleCloudProject
    self.remote_instance_name = None  # type: Optional[str]
    self.source_disk_names = []  # type: List[str]
    self.all_disks = False
    self.source_disks = []  # type: List[GoogleComputeDisk]
    self.exported_image_name = str()

  def Process(self) -> None:
    """Creates and exports disk image to the output bucket."""
    for source_disk in self.source_disks:
      image_object = self.analysis_project.compute.CreateImageFromDisk(
          source_disk)
      # If self.exported_image_name = None, default output_name is
      # {src_disk.name}-{TIMESTAMP('%Y%m%d%H%M%S')}.tar.gz
      image_object.ExportImage(
          self.gcs_output_location, output_name=self.exported_image_name)
      image_name = self.exported_image_name or image_object.name
      image_object.Delete()
      output_url = os.path.join(
          self.gcs_output_location,
          '{0:s}.tar.gz'.format(image_name))
      self.logger.info(f'Disk was exported to: {output_url}')
      container = containers.URL(path=output_url)
      self.StoreContainer(container)

  # pylint: disable=arguments-differ
  def SetUp(self,
            source_project_name: str,
            gcs_output_location: str,
            analysis_project_name: Optional[str]=None,
            source_disk_names: Optional[str]=None,
            remote_instance_name: Optional[str]=None,
            all_disks: bool=False,
            exported_image_name: Optional[str]=None) -> None:
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
    """
    self.source_project = gcp_project.GoogleCloudProject(source_project_name)
    if analysis_project_name:
      self.analysis_project = gcp_project.GoogleCloudProject(
          analysis_project_name)
    else:
      self.analysis_project = self.source_project
    self.remote_instance_name = remote_instance_name
    self.source_disk_names = []
    if source_disk_names:
      self.source_disk_names = source_disk_names.split(',')
    self.all_disks = all_disks

    self.source_disks = self._FindDisksToCopy()
    self.gcs_output_location = gcs_output_location
    if exported_image_name and len(self.source_disks) == 1:
      self.exported_image_name = exported_image_name

modules_manager.ModulesManager.RegisterModule(GoogleCloudDiskExport)
