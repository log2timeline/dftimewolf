# -*- coding: utf-8 -*-
"""Copies GCE Disks across projects."""

from typing import List, Optional, Dict, Type, Union

from googleapiclient.errors import HttpError
from libcloudforensics import errors as lcf_errors
from libcloudforensics.providers.gcp import forensics as gcp_forensics
from libcloudforensics.providers.gcp.internal import project as gcp_project

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
    stop_instances (bool): True if instances should be stopped after disks are
        copied.
    warned (bool): True if an error was encountered that prevents stopping
        instances when requested by stop_instances.
    failed_disks (list[str]): List of disks that failed.
    at_least_one_success (bool): True if at least one disk copy succeeded.
  """

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
    self.stop_instances = False
    self._gcp_label = {}  # type: Dict[str, str]
    self.warned = False  # type: bool
    self.failed_disks = []  # type: List[str]
    self.at_least_one_success = False

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            destination_project_name: Optional[str],
            source_project_name: str,
            destination_zone: str,
            remote_instance_names: Union[str, List[str], None],
            disk_names: Union[str, List[str], None],
            all_disks: bool,
            stop_instances: bool) -> None:
    """Sets up a GCEDiskCopyCollector.

    This method sets up the module for copying disks.

    If destination_project_name is not specified, destination_project will be
    the same as source_project.

    If remote_instance_names is specified, two behaviors are possible:
    * If no other parameters are specified, it will select the instance's boot
      disks
    * if all_disks is set to True, it will select all disks in the project
      that are attached to the instance

    Args:
      destination_project_name: Name of the project where disks will be copied
          to.
      source_project_name: Name of the remote project where the disks must be
          copied from.
      destination_zone: GCP zone in which disks should be copied to.
      remote_instance_names: Name of the instances in the remote project
          containing the disks to be copied.
      disk_names: Comma separated disk names to copy.
      all_disks: True if all disks attached to the source instance should be
          copied.
      stop_instances: Stop the target instance after copying disks.
    """
    if not (remote_instance_names or disk_names):
      self.ModuleError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)

    if stop_instances and not remote_instance_names:
      self.ModuleError(
          'You need to specify an instance name to stop the instance',
          critical=True)

    self.source_project = gcp_project.GoogleCloudProject(
        source_project_name, default_zone=destination_zone)
    if destination_project_name:
      self.destination_project = gcp_project.GoogleCloudProject(
          destination_project_name, default_zone=destination_zone)
    else:
      self.destination_project = self.source_project

    if isinstance(remote_instance_names, str):
      self.remote_instance_names = (
          remote_instance_names.split(',') if remote_instance_names else [])
    else:
      self.remote_instance_names = remote_instance_names or []

    if isinstance(disk_names, str):
      self.disk_names = disk_names.split(',') if disk_names else []
    else:
      self.disk_names = disk_names or []
    self.all_disks = all_disks
    self.stop_instances = stop_instances

  def PreProcess(self) -> None:
    """Organise any disks to be copied.

    Process uses GCEDisk containers, so we create those containers and store
    them in the state.
    """
    at_least_one_instance = False
    try:
      # Disks from the csv list passed in
      for d in self.disk_names:
        c = containers.GCEDisk(d, self.source_project.project_id)
        c.metadata['SOURCE_MACHINE'] = 'UNKNOWN_MACHINE'
        self.StoreContainer(c, for_self_only=True)

      # Disks from the instances passed in
      for i in self.remote_instance_names:
        try:
          for d in self._GetDisksFromInstance(i, self.all_disks):
            c = containers.GCEDisk(d, self.source_project.project_id)
            c.metadata['SOURCE_MACHINE'] = i
            self.StoreContainer(c, for_self_only=True)
            at_least_one_instance = True

        except lcf_errors.ResourceNotFoundError:
          message=(f'Instance "{i}" in {self.source_project.project_id} not '
                'found or insufficient permissions')
          self.PublishMessage(message, is_error=True)
      if self.remote_instance_names and not at_least_one_instance:
        self.ModuleError('No instances found with disks to copy.',
                         critical=True)
    except HttpError as exception:
      if exception.resp.status == 403:
        self.ModuleError(
            '403 response. Do you have appropriate permissions on the project?',
            critical=True)
      self.ModuleError(str(exception), critical=True)

  def Process(self, container: containers.GCEDisk
              ) -> None:  # pytype: disable=signature-mismatch
    """Copies a disk to the destination project.

    Args:
      container: GCEDisk container referencing the disk to copy.
    """
    if container.project != self.source_project.project_id:
      self.logger.debug(f"Skipping {container.name} not in source project")
    self.logger.info(f'Disk copy of {container.name} started...')

    try:
      new_disk = gcp_forensics.CreateDiskCopy(
          self.source_project.project_id,
          self.destination_project.project_id,
          self.destination_project.default_zone,
          disk_name=container.name)
      self.at_least_one_success = True
      self.PublishMessage(f'Disk {container.name} successfully copied to '
          f'{new_disk.name}')
      c = containers.GCEDisk(new_disk.name, self.destination_project.project_id)
      c.metadata.update(container.metadata)
      c.metadata['SOURCE_DISK'] = container.name
      self.StoreContainer(c)
    except lcf_errors.ResourceNotFoundError as exception:
      self.logger.error(f'Could not find disk "{container.name}": {exception}')
      self.warned = True
      self.ModuleError(str(exception), critical=False)
      self.failed_disks.append(container.name)
    except lcf_errors.ResourceCreationError as exception:
      self.logger.error(f'Could not create disk: {exception}')
      self.warned = True
      self.ModuleError(str(exception), critical=True)

  def PostProcess(self) -> None:
    """Stops instances where it was requested."""
    if self.stop_instances:
      self._StopInstances()

    if self.failed_disks:
      self.logger.warning('The following disks dould not be found: '
          f'{", ".join(self.failed_disks)}')

    if not self.at_least_one_success:
      self.ModuleError(
          'No successful disk copy operations completed.', critical=True)

  def _StopInstances(self) -> None:
    """Stops instances where it was requested."""
    if self.warned:
      self.logger.warning(
          'Not stopping instance due to previous warnings on disk copy')
      return

    for i in self.remote_instance_names:
      try:
        remote_instance = self.source_project.compute.GetInstance(i)
        # TODO(dfjxs): Account for GKE Nodes
        remote_instance.Stop()
      except lcf_errors.InstanceStateChangeError as exception:
        self.ModuleError(str(exception), critical=False)
      self.logger.info(f'Stopped instance {i}')

  def _GetDisksFromInstance(
      self,
      instance_name: str,
      all_disks: bool) -> List[str]:
    """Gets disks to copy based on an instance name.

    Args:
      instance_name (str): Name of the instance to get the disks from.
      all_disks (bool): If set, get all disks attached to the instance. If
          False, get only the instance's boot disk.

    Returns:
      list[str]: List of disk names to copy.
    """
    try:
      remote_instance = self.source_project.compute.GetInstance(instance_name)
    except RuntimeError as exception:
      self.ModuleError(str(exception), critical=True)

    if all_disks:
      return [d.name for d in list(remote_instance.ListDisks().values())]
    return [remote_instance.GetBootDisk().name]

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    return containers.GCEDisk

  def GetThreadPoolSize(self) -> int:
    return 15  # Arbitrary


modules_manager.ModulesManager.RegisterModule(GCEDiskCopy)
