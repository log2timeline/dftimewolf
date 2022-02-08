# -*- coding: utf-8 -*-
"""Copies GCE Disks across projects."""

from typing import List, Optional, Dict, Type

from google.auth.exceptions import DefaultCredentialsError, RefreshError
from googleapiclient.errors import HttpError
from libcloudforensics import errors as lcf_errors
from libcloudforensics.providers.gcp import forensics as gcp_forensics
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class GCEDiskCopy(module.ThreadAwareModule):
  """Google Compute Engine Disk collector.

  Attributes:
    destination_project (gcp.GoogleCloudProject): Project to copy the disks to.
    source_project (gcp.GoogleCloudProject): Source project to copy disks from.
    remote_instance_names (str): Instance that needs forensicating.
    disk_names (list[str]): Comma-separated list of disk names to copy.
    all_disks (bool): True if all disks attached to the source
        instance should be copied.
  """

  _ANALYSIS_VM_CONTAINER_ATTRIBUTE_NAME = 'Analysis VM'
  _ANALYSIS_VM_CONTAINER_ATTRIBUTE_TYPE = 'text'

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a Google Cloud Platform (GCP) collector.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GCEDiskCopy, self).__init__(
        state, name=name, critical=critical)
    self.destination_project = None  # type: gcp_project.GoogleCloudProject
    self.source_project = None  # type: gcp_project.GoogleCloudProject
    self.remote_instance_names = []  # type: List[str]
    self.disk_names = []  # type: List[str]
    self.all_disks = False
    self.stop_instance = False
    self._gcp_label = {}  # type: Dict[str, str]
    self.warned = False  # type: bool

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            destination_project_name: str,
            source_project_name: str,
            destination_zone: str='us-central1-f',
            remote_instance_names: Optional[str]=None,
            disk_names: Optional[str]=None,
            all_disks: bool=False,
            stop_instance: bool=False) -> None:
    """Sets up a GCEDiskCopyCollector.

    This method sets up the module for copying disks.

    If destination_project_name is not specified, destination_project will be
    the same as source_project.

    If disk_names is specified, it will copy the corresponding disks from the
    project, ignoring disks belonging to any specific instances.

    If remote_instance_names is specified, two behaviors are possible:
    * If no other parameters are specified, it will select the instance's boot
      disks
    * if all_disks is set to True, it will select all disks in the project
      that are attached to the instance

    disk_names takes precedence over instance_names

    Args:
      destination_project_name (str): Optional. Name of the project where disks
          will be copied to.
      source_project_name (str): Name of the remote project where the disks
          must be copied from.
      destination_zone (Optional[str]): Optional. GCP zone in which disks should
          be copied to. Default is us-central1-f.
      s (Optional[str]): Optional. Name of the instance in
          the remote project containing the disks to be copied.
      disk_names (Optional[str]): Optional. Comma separated disk names to copy.
      all_disks (Optional[bool]): Optional. True if all disks attached to the
          source instance should be copied.
      stop_instance (Optional[bool]): Optional. Stop the target instance after
          copying disks.
    """
    if not (remote_instance_names or disk_names):
      self.ModuleError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)
      return

    if stop_instance and not remote_instance_names:
      self.ModuleError(
          'You need to specify an instance name to stop the instance',
          critical=True)
      return

    self.source_project = gcp_project.GoogleCloudProject(
        source_project_name, default_zone=destination_zone)
    if destination_project_name:
      self.destination_project = gcp_project.GoogleCloudProject(
          destination_project_name, default_zone=destination_zone)
    else:
      self.destination_project = self.source_project

    self.remote_instance_names = (
        remote_instance_names.split(',') if remote_instance_names else [])
    self.disk_names = disk_names.split(',') if disk_names else []
    self.all_disks = all_disks
    self.stop_instance = stop_instance

  def PreProcess(self) -> None:
    """Organise any disks to be copied.

    Process uses GCEDisk containers, so we create those containers and store
    them in the state.
    """
    try:
      # Disks from the csv list passed in
      for d in self.disk_names:
        self.state.StoreContainer(containers.GCEDisk(d))

      # Disks from the instances passed in
      for i in self.remote_instance_names:
        try:
          for d in self._GetDisksFromInstance(i, self.all_disks):
            self.state.StoreContainer(containers.GCEDisk(d))

        except lcf_errors.ResourceNotFoundError:
          self.ModuleError(
            message=f'Instance "{i}" not found or insufficient permissions',
            critical=True)
          return
    except (RefreshError, DefaultCredentialsError) as exception:
      msg = ('Something is wrong with your Application Default Credentials. '
             'Try running:\n  $ gcloud auth application-default login\n')
      msg += str(exception)
      self.ModuleError(msg, critical=True)
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

  def Process(self, container: containers.GCEDisk) -> None:
    """Copies a disk to the destination project.

    Args:
      container: GCEDisk container referencing the disk to copy.
    """
    self.logger.info('Disk copy of {0:s} started...'.format(container.name))

    try:
      new_disk = gcp_forensics.CreateDiskCopy(
          self.source_project.project_id,
          self.destination_project.project_id,
          self.destination_project.default_zone,
          disk_name=container.name)
    except lcf_errors.ResourceCreationError as exception:
      self.logger.warning('Could not create disk: {0!s}'.format(exception))
      self.warned = True

    self.logger.success('Disk {0:s} successfully copied to {1:s}'.format(
        container.name, new_disk.name))
    self.state.StoreContainer(containers.GCEDisk(new_disk.name))

  def PostProcess(self) -> None:
    if self.stop_instance and not self.warned:
      for i in self.remote_instance_names:
        try:
          remote_instance = self.source_project.compute.GetInstance(i)
          # TODO(dfjxs): Account for GKE Nodes
          remote_instance.Stop()
        except lcf_errors.InstanceStateChangeError as exception:
          self.ModuleError(str(exception), critical=False)
        self.logger.success(
            'Stopped instance {0:s}'.format(i))
    elif self.stop_instance and self.warned:
      self.logger.warning(
          'Not stopping instance due to previous warnings on disk copy')

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
      remote_instance = self.source_project.compute.GetInstance(instance_name)
    except RuntimeError as exception:
      self.ModuleError(str(exception), critical=True)

    if all_disks:
      return [d.name for d in list(remote_instance.ListDisks().values())]
    return [remote_instance.GetBootDisk().name]

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.GCEDisk

  def GetThreadPoolSize(self) -> int:
    return 15  # Arbitrary

  @staticmethod
  def KeepThreadedContainersInState() -> bool:
    return False


modules_manager.ModulesManager.RegisterModule(GCEDiskCopy)
