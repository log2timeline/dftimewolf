# -*- coding: utf-8 -*-
"""Classes for storing GCP disks into containers."""

from typing import List, Optional

from googleapiclient.errors import HttpError
from libcloudforensics.errors import ResourceNotFoundError
from libcloudforensics.providers.gcp.internal import compute
from libcloudforensics.providers.gcp.internal import project as gcp_project

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class GCEDiskCollector(module.BaseModule):

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str] = None,
               critical: Optional[bool] = False):
    """Initializes a GCE disk collector.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GCEDiskCollector, self).__init__(state, name=name, critical=critical)
    self.remote_project = None  # type: gcp_project.GoogleCloudProject
    self.remote_instance_name = None  # type: Optional[str]
    self.disk_names = []  # type: List[str]
    self.all_disks = False

  def Process(self) -> None:
    """Stores disks in a container for the next module."""
    for disk in self._FindDisksToCopy():
      self.state.StoreContainer(containers.GCEDisk(disk.name))

  def SetUp(self,
            remote_project_name: str,
            remote_instance_name: Optional[str] = None,
            disk_names: Optional[str] = None,
            all_disks: bool = False) -> None:
    """Sets up a GCE disk collector.

    This method initializes this object's attributes and checks whether the
    specified instance exists.

    Args:
      remote_project_name (str): name of the remote project where the disks
          must be copied from.
      remote_instance_name (Optional[str]): Optional. Name of the instance in
          the remote project containing the disks to be copied.
      disk_names (Optional[str]): Optional. Comma separated disk names to copy.
      all_disks (Optional[bool]): Optional. True if all disks attached to the
          source instance should be copied.
    """
    if not (remote_instance_name or disk_names):
      self.ModuleError(
        'You need to specify at least an instance name or disks to copy',
        critical=True)
      return

    self.remote_project = gcp_project.GoogleCloudProject(remote_project_name)
    self.remote_instance_name = remote_instance_name
    self.disk_names = disk_names.split(',') if disk_names else []
    self.all_disks = all_disks

    try:
      if self.remote_instance_name:
        self.remote_project.compute.GetInstance(self.remote_instance_name)
    except ResourceNotFoundError:
      self.ModuleError(
        message='Instance "{0:s}" not found or insufficient permissions'.format(
          self.remote_instance_name),
        critical=True)
      return

  def _GetDisksFromNames(
      self, disk_names: List[str]) -> List[compute.GoogleComputeDisk]:
    """Gets disks from a project by disk name.

    Args:
      disk_names (list[str]): List of disk names to get from the project.

    Returns:
      list[compute.GoogleComputeDisk]: List of GoogleComputeDisk objects to
          copy.
    """
    disks = []
    for name in disk_names:
      try:
        disks.append(self.remote_project.compute.GetDisk(name))
      except RuntimeError:
        self.ModuleError(
          'Disk "{0:s}" was not found in project {1:s}'.format(
            name, self.remote_project.project_id),
          critical=True)
    return disks

  def _GetDisksFromInstance(
      self,
      instance_name: str,
      all_disks: bool) -> List[compute.GoogleComputeDisk]:
    """Gets disks to copy based on an instance name.

    Args:
      instance_name (str): Name of the instance to get the disks from.
      all_disks (bool): If set, get all disks attached to the instance. If
          False, get only the instance's boot disk.

    Returns:
      list[compute.GoogleComputeDisk]: List of compute.GoogleComputeDisk
          objects to copy.
    """
    try:
      remote_instance = self.remote_project.compute.GetInstance(instance_name)
    except RuntimeError as exception:
      self.ModuleError(str(exception), critical=True)

    if all_disks:
      return list(remote_instance.ListDisks().values())
    return [remote_instance.GetBootDisk()]

  def _FindDisksToCopy(self) -> List[compute.GoogleComputeDisk]:
    """Determines which disks to copy depending on object attributes.

    Returns:
      list[compute.GoogleComputeDisk]: the disks to copy to the
          analysis project.
    """
    if not (self.remote_instance_name or self.disk_names):
      self.ModuleError(
        'You need to specify at least an instance name or disks to copy',
        critical=True)

    disks_to_copy = []

    try:

      if self.disk_names:
        disks_to_copy = self._GetDisksFromNames(self.disk_names)

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


modules_manager.ModulesManager.RegisterModule(GCEDiskCollector)
