# -*- coding: utf-8 -*-
"""Export disk image from a GCP project to Google Cloud Storage."""


import os
from libcloudforensics.providers.gcp.internal import project as gcp_project
from googleapiclient.errors import HttpError
from dftimewolf.lib import module
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
    self.remote_instance_name = None
    self.source_disk_names = []
    self.all_disks = False
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
            source_disk_names=None,
            remote_instance_name=None,
            all_disks=False,
            exported_image_name=None):
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

    if not (remote_instance_name or source_disk_names):
      self.ModuleError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)

    self.remote_instance_name = remote_instance_name
    source_disk_names = source_disk_names.split(
        ',') if source_disk_names else []
    self.source_disk_names = source_disk_names
    self.all_disks = all_disks

    self.source_disks = self._FindDisksToCopy()
    self.gcs_output_location = gcs_output_location
    if exported_image_name and len(self.source_disks) == 1:
      self.exported_image_name = exported_image_name

  def _GetDisksFromNames(self, source_disk_names):
    """Gets disks from a project by disk name.

    Args:
      source_disk_names (list[str]): List of disk names to get from the project.

    Returns:
      list[GoogleComputeDisk]: List of GoogleComputeDisk objects to copy.
    """
    disks = []
    for name in source_disk_names:
      try:
        disks.append(self.source_project.compute.GetDisk(name))
      except RuntimeError:
        self.ModuleError(
            'Disk "{0:s}" was not found in project {1:s}'.format(
                name, self.source_project.project_id),
            critical=True)
    return disks

  def _GetDisksFromInstance(self, instance_name, all_disks):
    """Gets disks to copy based on an instance name.

    Args:
      instance_name (str): Name of the instance to get the disks from.
      all_disks (bool): If set, get all disks attached to the instance. If
          False, get only the instance's boot disk.

    Returns:
      list[GoogleComputeDisk]: List of GoogleComputeDisk objects to copy.
    """
    try:
      remote_instance = self.source_project.compute.GetInstance(instance_name)
    except RuntimeError as exception:
      self.ModuleError(str(exception), critical=True)

    if all_disks:
      return list(remote_instance.ListDisks().values())
    return [remote_instance.GetBootDisk()]

  def _FindDisksToCopy(self):
    """Determines which disks to copy depending on object attributes.

    Returns:
      list[GoogleComputeDisk]: the disks to copy to the
          analysis project.
    """
    if not (self.remote_instance_name or self.source_disk_names):
      self.ModuleError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)

    disks_to_copy = []

    try:

      if self.source_disk_names:
        disks_to_copy = self._GetDisksFromNames(self.source_disk_names)

      elif self.remote_instance_name:
        disks_to_copy = self._GetDisksFromInstance(self.remote_instance_name,
                                                   self.all_disks)

    except HttpError as exception:
      if exception.resp.status == 403:
        self.ModuleError(
            '403 response. Do you have appropriate permissions on the project?',
            critical=True)
      if exception.resp.status == 404:
        self.ModuleError(
            'GCP resource not found. Maybe a typo in the project / instance / '
            'disk name?',
            critical=True)
      self.ModuleError(str(exception), critical=True)

    if not disks_to_copy:
      self.ModuleError(
          'Could not find any disks to copy', critical=True)

    return disks_to_copy

modules_manager.ModulesManager.RegisterModule(GoogleCloudDiskExport)
