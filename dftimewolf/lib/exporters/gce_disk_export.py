# -*- coding: utf-8 -*-
"""Export disk image from a GCP project to Google Cloud Storage."""


import os
from libcloudforensics.providers.gcp.internal import project as gcp_project
from dftimewolf import config
from dftimewolf.lib import state as state_mod
from dftimewolf.lib import module
from dftimewolf.lib.collectors import gcloud
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager


class GoogleCloudDiskExport(module.BaseModule):
  """Google Cloud Platform (GCP) Disk Export.

  Attributes:
    source_project (gcp_project.GoogleCloudProject): Source project
        containing the disk/s to export.
    gcs_output_location (str): Google Cloud Storage parent bucket/folder
        path of the exported image.
    analysis_project (gcp_project.GoogleCloudProject): Project where the
        disk image is created then exported.
        If not exit, source_project will be used.
    source_disks (list[gcp_project.compute.GoogleComputeDisk]): List of disks
        to be exported.
    exported_image_name (Optional[str]): Optional. Name of the output file, must
        comply with ^[A-Za-z0-9-]*$' and '.tar.gz' will be appended to the name.
        Default, if not exist or if more than one disk is selected, exported
        image name as "exported-image-{TIMESTAMP('%Y%m%d%H%M%S')}".
  """

  def __init__(self, state, critical=False):
    """Initializes a Google Cloud Platform (GCP) Disk Export.

    Args:
      state (DFTimewolfState): recipe state.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GoogleCloudDiskExport, self).__init__(state, critical=critical)
    self.source_project = None
    self.gcs_output_location = None
    self.analysis_project = None
    self.source_disks = []
    self.exported_image_name = None

  def Process(self):
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
      self.logger.info('Disk was exported to: {0:s}'.format(output_url))
      container = containers.URL(path=output_url)
      self.state.StoreContainer(container)

  # pylint: disable=arguments-differ
  def SetUp(self,
            source_project_name,
            gcs_output_location,
            analysis_project_name=None,
            disk_names=None,
            remote_instance_name=None,
            all_disks=False,
            exported_image_name=None):
    """Sets up a Google Cloud Platform (GCP) Disk Export.

    This method creates the required objects to initialize
    the GoogleCloudDiskExport class attributes.

    If the analysis_project_name is not specified it will use the
    source_project_name instead.

    If disk_names is specified, it will copy the corresponding disks from the
    project, ignoring disks belonging to any specific instances.

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
          disk image is created then exported. Default,
          source_project_name will be used.
      disk_names (Optional[str]): Optional. Comma separated disk names to copy.
          Default is None.
      remote_instance_name (Optional[str]): Optional. Instance in source
          project to export its disks. Default, if not exist, disk_names
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

    if not (remote_instance_name or disk_names):
      self.state.AddError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)
      return

    init_state = state_mod.DFTimewolfState(config.Config)
    gcloud_collector = gcloud.GoogleCloudCollector(init_state)
    gcloud_collector.SetUp(
        analysis_project_name=self.analysis_project.project_id,
        remote_project_name=self.source_project.project_id,
        create_analysis_vm=False,
        disk_names=disk_names,
        all_disks=all_disks,
        remote_instance_name=remote_instance_name)

    self.source_disks = gcloud_collector.FindDisksToCopy()
    self.gcs_output_location = gcs_output_location
    if exported_image_name and len(self.source_disks) == 1:
      self.exported_image_name = exported_image_name

modules_manager.ModulesManager.RegisterModule(GoogleCloudDiskExport)
