# -*- coding: utf-8 -*-
"""Base class to Export Compute disk images to Google Cloud Storage."""
import os
from typing import List, Optional
from googleapiclient.errors import HttpError
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeDisk  # pylint: disable=line-too-long
from dftimewolf.lib import module
from dftimewolf.lib.state import DFTimewolfState


#pylint: disable=abstract-method
class GoogleCloudDiskExportBase(module.BaseModule):
  """Google Cloud Platform (GCP) disk export base class.

  Attributes:
    source_project (gcp_project.GoogleCloudProject): Source project
        containing the disk/s to export.
    remote_instance_name (str): Instance that needs forensicating.
    source_disk_names (list[str]): Comma-separated list of disk names to copy.
    all_disks (bool): True if all disks attached to the source
        instance should be copied.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes GCP disk export base class.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GoogleCloudDiskExportBase, self).__init__(
        state, name=name, critical=critical)
    self.source_project = None  # type: gcp_project.GoogleCloudProject
    self.remote_instance_name = None  # type: Optional[str]
    self.source_disk_names = []  # type: List[str]
    self.all_disks = False

  def _GetDisksFromNames(
      self, source_disk_names: List[str]) -> List[GoogleComputeDisk]:
    """Gets disks from a project by disk name.

    Args:
      source_disk_names: List of disk names to get from the project.

    Returns:
      List of GoogleComputeDisk objects to copy.
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

  def _GetDisksFromInstance(
      self, instance_name: str, all_disks: bool) -> List[GoogleComputeDisk]:
    """Gets disks to copy based on an instance name.

    Args:
      instance_name : Name of the instance to get the disks from.
      all_disks : If set, get all disks attached to the instance. If
          False, get only the instance's boot disk.

    Returns:
      list: List of GoogleComputeDisk objects to copy.
    """
    try:
      remote_instance = self.source_project.compute.GetInstance(instance_name)
    except RuntimeError as exception:
      self.ModuleError(str(exception), critical=True)

    if all_disks:
      return list(remote_instance.ListDisks().values())
    return [remote_instance.GetBootDisk()]

  def _FindDisksToCopy(self) -> List[GoogleComputeDisk]:
    """Determines which disks to copy depending on object attributes.

    Returns:
      The disks to copy to the analysis project.
    """
    if not (self.remote_instance_name or self.source_disk_names):
      self.ModuleError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)
    if self.remote_instance_name and self.source_disk_names:
      self.ModuleError(
          ('Both --source_disk_names and --remote_instance_name are provided, '
          'remote_instance_name will be ignored in favour of '
          'source_disk_names.'),
          critical=False)
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

  def _ReadExportScript(self, filename: str) -> str:
    """Reads the Startup script used to export disks to GCS.

    Args:
      filename: name of the file to read.
      
    Raises:
      OSError: If the script cannot be opened, read or closed.
    """
    try:
      path = os.path.join(
          os.path.dirname(os.path.realpath(__file__)), filename)
      with open(path, encoding='utf-8') as startup_script:
        return startup_script.read()
    except OSError as exception:
      raise OSError(
          'Could not open/read/close the Export script {0:s}: {1:s}'.format(
              path, str(exception))) from exception

  def _DetachDisks(self, disks: List[GoogleComputeDisk]) -> None:
    """Detaches disks from VMs in case they are attached.

    Args:
      disks: disks to detach.
    """
    try:
      for disk in disks:
        users = disk.GetValue('users')
        if users:
          instance_name = users[0].split('/')[-1]
          instance = self.source_project.compute.GetInstance(instance_name)
          self.logger.warning(
            'Disk "{0:s}" will be detached from instance "{1:s}"'.format(
              disk.name, instance_name))
          instance.DetachDisk(disk)
    except HttpError as exception:
      if exception.resp.status == 400:
        self.ModuleError(
            ('400 response. To detach the boot disk, the instance must be in '
            'TERMINATED state: {0!s}'.format(exception)), critical=True)
      self.ModuleError(str(exception), critical=True)

  def _VerifyDisksInSameZone(self, disks: List[GoogleComputeDisk]) -> bool:
    """Verifies that all dicts are in the same Zone.

    Args:
      disks: compute disks.
    """
    return all(disk.zone == disks[0].zone for disk in disks)
