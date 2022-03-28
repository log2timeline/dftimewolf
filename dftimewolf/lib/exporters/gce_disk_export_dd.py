# -*- coding: utf-8 -*-
"""Export disk image from a GCP project to Google Cloud Storage (GCS).

The export is performed via bit streaming the disk bytes to GCS.
This will allow getting a disk image out of the project in case both
organization policies `constraints/compute.storageResourceUseRestrictions`
and `constraints/compute.trustedImageProjects` are enforced and in case
OsLogin is allowed only for the organization users while the analyst is an
external user with no roles/compute.osLoginExternalUser role.
The export process happen in the following order:
  - Start a new "Export" VM in the compromised project. This module allows
    the analyst to specify the source image of the machine, this is needed
    in case `constraints/compute.trustedImageProjects` is enforced.
  - The Export VM will have evidence disks attached in read-only mode.
  - Print the output path to the user and some information on how to track
    the disk export progress in case the terminal session is interrupted.
  - A startup script in the export machine will:
    - Enumerate all, non-boot, disks attached to the VM.
    - Read the disk bytes and stream them to a GCS bucket.
    - Verify the hash of the exported disk in GCS against the source disk hash.
"""


import os
import time
from typing import List, Optional

from libcloudforensics.providers.gcp.internal import common as gcp_common
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeDisk

from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState
from dftimewolf.lib.exporters.gce_disk_export_base import GoogleCloudDiskExportBase  # pylint: disable=line-too-long
from utils import utils


_EXPORT_STARTUP_SCRIPT = 'export_machine_startup_script.sh'

class GoogleCloudDiskExportStream(GoogleCloudDiskExportBase):
  """Google Cloud Platform (GCP) disk bit-stream export.

  Attributes:
    source_project (gcp_project.GoogleCloudProject): Source project
        containing the disk/s to export.
    gcs_output_location (str): Google Cloud Storage parent bucket/folder
        path of the exported image.
    remote_instance_name (str): Instance that needs analysis.
    source_disk_names (list[str]): Comma-separated list of disk names to copy.
    all_disks (bool): True if all disks attached to the source
        instance should be copied.
    source_disks (list[gcp_project.compute.GoogleComputeDisk]): List of disks
        to be exported.
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
    super(GoogleCloudDiskExportStream, self).__init__(
        state, name=name, critical=critical)
    self.source_project = None  # type: gcp_project.GoogleCloudProject
    self.gcs_output_location = str()
    self.remote_instance_name = None  # type: Optional[str]
    self.source_disk_names = []  # type: List[str]
    self.all_disks = False
    self.source_disks = []  # type: List[GoogleComputeDisk]
    self.startup_script = str()
    self.boot_image_project = None # type: Optional[str]
    self.boot_image_family = None # type: Optional[str]

  # pylint: disable=arguments-differ
  def SetUp(self,
            source_project_name: str,
            gcs_output_location: str,
            source_disk_names: Optional[str]=None,
            remote_instance_name: Optional[str]=None,
            all_disks: bool=False,
            boot_image_project: Optional[str]=None,
            boot_image_family: Optional[str]=None) -> None:
    """Sets up a Google Cloud Platform (GCP) Disk Export.

    This method creates the required objects to initialize
    the GoogleCloudDiskExportStream class attributes.

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
      source_disk_names (Optional[str]): Optional. Comma separated disk names
          to copy.Default is None.
      remote_instance_name (Optional[str]): Optional. Instance in source
          project to export its disks. Default, if not exist, source_disk_names
          will be used.
      all_disks (Optional[bool]): Optional. True if all disks attached to
          the source instance should be copied. Default is False. If False
          and remote_instance_name is provided it will select the instance's
          boot disk.
      boot_image_project: Name of the project where the boot disk image is
          stored.
      boot_image_family: Name of the image to use to create the boot disk.
    """
    self.source_project = gcp_project.GoogleCloudProject(source_project_name)
    self.remote_instance_name = remote_instance_name
    self.source_disk_names = []
    if source_disk_names:
      self.source_disk_names = source_disk_names.split(',')
    self.all_disks = all_disks

    self.source_disks = self._FindDisksToCopy()
    if not self._VerifyDisksInSameZone(self.source_disks):
      self.ModuleError('All disks need to be in the same Zone.', critical=True)
    self._DetachDisks(self.source_disks)
    # Add a trailing slash if it's not already there.
    self.gcs_output_location = os.path.join(gcs_output_location, '')
    self.startup_script = utils.ReadExportScript(_EXPORT_STARTUP_SCRIPT)
    self.boot_image_project = boot_image_project
    self.boot_image_family = boot_image_family

  def Process(self) -> None:
    """Creates and exports disk image to the output bucket."""
    export_instance_name = gcp_common.GenerateUniqueInstanceName(
      'dftimewolf-export')
    self.startup_script = self.startup_script.format(
      project_id=self.source_project.project_id,
      archive_bucket=self.gcs_output_location,
      zone=self.source_disks[0].zone,
      instance_name=export_instance_name)
    export_instance = self.source_project.compute.CreateInstanceFromArguments(
      instance_name=export_instance_name,
      machine_type='{0:s}-{1:d}'.format('e2-standard', 16),
      zone=self.source_disks[0].zone,
      boot_disk_type='pd-standard',
      boot_disk_size=20,
      boot_image_project=self.boot_image_project,
      boot_image_family=self.boot_image_family,
      metadata={'startup-script': self.startup_script},
      data_disks=self.source_disks,
      additional_scopes=['https://www.googleapis.com/auth/cloud-platform'])

    while not self._ExportJobFinished():
      self.logger.info(
        ('Waiting for export instance {0:s} to finish exporting disks. '
        'This can take up-to few minutes or hours depending on disks size. '
        'All non-boot disk must have "archive" and "archive_hash_verified" '
        'labels equal "true" for the export job to finish.').format(
          export_instance.name))
      time.sleep(30)

    export_instace_api_object = export_instance.GetOperation()
    for disk in self.source_disks:
      for key_value_dict in export_instace_api_object.get(
        'metadata', {}).get('items', []):
        if not key_value_dict['key'].startswith('archive_path_'):
          continue
        # Reading the last value of the partition result, which is sometimes
        # prefixed with special characters making its position inconsistent.
        archived_disk = key_value_dict['key'].partition('archive_path_')[-1]
        if archived_disk == disk.name:
          value_tuple = key_value_dict['value'].partition(r'\n')
          disk_path_gcs = value_tuple[-1]
          incident_id = value_tuple[0]
          container = containers.URL(path=disk_path_gcs)
          self.state.StoreContainer(container)
          self.logger.success(
              ('Disk "{0:s}" exported. Incident ID: {1:s} '
              'Output path: {2:s}. To import this disk as '
              'an image in a different project. Please use: \n'
              'gcloud compute images import {0:s}'
              '--source-file {2:s} --data-disk '
              '--project={{PROJECT_ID}}').format(
              archived_disk, incident_id , disk_path_gcs))

    export_instance.Delete()

  def _ExportJobFinished(self) -> bool:
    """Determines if export job has finished.

    Returns:
      True if export is done, else False.
    """
    for disk in self.source_disks:
      labels_dict = disk.GetLabels()
      label_value = labels_dict.get('archive_hash_verified', False)
      if not label_value  or label_value != 'true':
        return False # no need to continue checking other labels
    return True

modules_manager.ModulesManager.RegisterModule(GoogleCloudDiskExportStream)
