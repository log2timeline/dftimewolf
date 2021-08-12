# -*- coding: utf-8 -*-
"""Creates an analysis VM and copies Azure disks to it for analysis."""

from typing import List, Optional

from libcloudforensics.providers.azure import forensics as az_forensics
from libcloudforensics.providers.azure.internal import account
from libcloudforensics.providers.azure.internal import compute

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class AzureCollector(module.BaseModule):
  """Microsoft Azure Collector.

  Attributes:
    remote_profile_name (str): The Azure account in which the disk(s)
        exist(s). This is the profile name that is defined in your credentials
        file.
    source_account (AZAccount): The AZAccount object that represents the
        source account in which the disk(s) exist(s).
    incident_id (str): Incident identifier used to name the analysis VM.
    remote_instance_name (str): Instance ID that needs forensicating.
    disk_names (list[str]): List of disk names to copy.
    all_disks (bool): True if all disk attached to the source
        instance should be copied.
    analysis_profile_name (str): The Azure account in which to create the
        analysis VM. This is the profile name that is defined in your
        credentials file.
    analysis_region (str): The Azure region in which to create the VM.
    analysis_resource_group_name (str): The Azure resource group name in
        which to create the VM.
    analysis_vm (AZVirtualMachine): Analysis VM to which the disk copy will be
        attached.
  """

  _ANALYSIS_VM_CONTAINER_ATTRIBUTE_NAME = 'Analysis VM'
  _ANALYSIS_VM_CONTAINER_ATTRIBUTE_TYPE = 'text'

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a Microsoft Azure collector.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(AzureCollector, self).__init__(state, critical=critical)
    self.remote_profile_name = str()
    self.source_account = None  # type: account.AZAccount
    self.incident_id = str()
    self.remote_instance_name = str()  # type: Optional[str]
    self.disk_names = []  # type: List[str]
    self.all_disks = False
    self.analysis_profile_name = str()
    self.analysis_region = str()  # type: Optional[str]
    self.analysis_resource_group_name = str()
    self.analysis_vm = None  # type: compute.AZComputeVirtualMachine

  def Process(self) -> None:
    """Copies a disk to the analysis account."""
    for disk in self._FindDisksToCopy():
      self.logger.info('Disk copy of {0:s} started...'.format(disk.name))
      new_disk = az_forensics.CreateDiskCopy(
          self.analysis_resource_group_name,
          disk_name=disk.name,
          region=self.analysis_region,
          src_profile=self.remote_profile_name,
          dst_profile=self.analysis_profile_name
      )
      self.logger.info('Disk {0:s} successfully copied to {1:s}'.format(
          disk.name, new_disk.name))
      self.analysis_vm.AttachDisk(new_disk)
      container = containers.ForensicsVM(
          name=self.analysis_vm.name,
          evidence_disk=new_disk,
          platform='azure')
      self.state.StoreContainer(container)

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            remote_profile_name: str,
            analysis_resource_group_name: str,
            incident_id: str,
            ssh_public_key: str,
            remote_instance_name: Optional[str]=None,
            disk_names: Optional[str]=None,
            all_disks: bool=False,
            analysis_profile_name: Optional[str]=None,
            analysis_region: Optional[str]=None,
            boot_disk_size: int=50,
            cpu_cores: int=4,
            memory_in_mb: int=8192) -> None:
    """Sets up a Microsoft Azure collector.

    This method creates and starts an analysis VM in the analysis account and
    selects disks to copy from the remote account.

    If disk_names is specified, it will copy the corresponding disks from the
    account, ignoring disks belonging to any specific instances.

    If remote_instance_name is specified, two behaviors are possible:
    * If no other parameters are specified, it will select the instance's boot
      disk
    * if all_disks is set to True, it will select all disks in the account
      that are attached to the instance

    disk_names takes precedence over instance_names

    Args:
      remote_profile_name (str): The Azure account in which the disk(s)
          exist(s). This is the profile name that is defined in your credentials
          file.
      analysis_resource_group_name (str): The Azure resource group name in
          which to create the VM.
      incident_id (str): Incident identifier used to name the analysis VM.
      ssh_public_key (str): The public SSH key to attach to the instance.
      remote_instance_name (str): Instance ID that needs forensicating.
      disk_names (str): Comma-separated list of disk names to copy.
      all_disks (bool): True if all disk attached to the source
          instance should be copied.
      analysis_profile_name (str): The Azure account in which to create the
          analysis VM. This is the profile name that is defined in your
          credentials file.
      analysis_region (str): The Azure region in which to create the VM.
      boot_disk_size (int): Optional. The size (in GB) of the boot disk
          for the analysis VM. Default is 50 GB.
      cpu_cores (int): Optional. The number of CPU cores to use for the
          analysis VM. Default is 4.
      memory_in_mb (int): Optional. The amount of memory in mb to use for the
          analysis VM. Default is 8Gb.
    """
    if not (remote_instance_name or disk_names):
      self.ModuleError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)
      return

    if not ssh_public_key:
      self.ModuleError('You need to specify a SSH public key to add to the '
                       'VM.', critical=True)
      return

    if not (remote_profile_name and analysis_resource_group_name):
      self.ModuleError('You must specify "remote_profile_name" and '
                       '"analysis_resource_group_name" parameters',
                       critical=True)
      return

    self.remote_profile_name = remote_profile_name
    self.analysis_resource_group_name = analysis_resource_group_name
    self.source_account = account.AZAccount(
        self.analysis_resource_group_name,
        profile_name=self.remote_profile_name)

    self.incident_id = incident_id
    self.remote_instance_name = remote_instance_name

    self.disk_names = disk_names.split(',') if disk_names else []
    self.all_disks = all_disks
    self.analysis_region = analysis_region
    self.analysis_profile_name = analysis_profile_name or remote_profile_name

    analysis_vm_name = 'azure-forensics-vm-{0:s}'.format(self.incident_id)
    print('Your analysis VM will be: {0:s}'.format(analysis_vm_name))
    self.state.StoreContainer(
        containers.TicketAttribute(
            name=self._ANALYSIS_VM_CONTAINER_ATTRIBUTE_NAME,
            type_=self._ANALYSIS_VM_CONTAINER_ATTRIBUTE_TYPE,
            value=analysis_vm_name))
    self.analysis_vm, _ = az_forensics.StartAnalysisVm(
        self.analysis_resource_group_name,
        analysis_vm_name,
        boot_disk_size,
        ssh_public_key=ssh_public_key,
        cpu_cores=cpu_cores,
        memory_in_mb=memory_in_mb,
        region=self.analysis_region,
        dst_profile=self.analysis_profile_name,
    )

  def _GetDisksFromNames(self,
                         disk_names: List[str]) -> List[compute.AZComputeDisk]:
    """Gets disks from an Azure account by disk name.

    Args:
      disk_names (list[str]): List of disk names to get from the account.

    Returns:
      list[AZDisk]: List of AZDisk objects to copy.
    """
    disks = []
    for name in disk_names:
      try:
        disks.append(self.source_account.compute.GetDisk(name))
      except RuntimeError:
        self.ModuleError(
            'Disk "{0:s}" was not found in subscription {1:s}'.format(
                name, self.source_account.subscription_id),
            critical=True)
        return []
    return disks

  def _GetDisksFromInstance(self,
                            instance_name: str,
                            all_disks: bool) -> List[compute.AZComputeDisk]:
    """Gets disks to copy based on an instance name.

    Args:
      instance_name (str): Name of the instance to get the disks from.
      all_disks (bool): If set, get all disks attached to the instance. If
          False, get only the instance's boot disk.

    Returns:
      list[AZDisk]: List of AZDisk objects to copy.
    """
    try:
      remote_instance = self.source_account.compute.GetInstance(instance_name)
    except RuntimeError as exception:
      self.ModuleError(str(exception), critical=True)
      return []

    if all_disks:
      return list(remote_instance.ListDisks().values())
    return [remote_instance.GetBootDisk()]

  def _FindDisksToCopy(self) -> List[compute.AZComputeDisk]:
    """Determines which disks to copy depending on object attributes.

    Returns:
      list[AZDisk]: the disks to copy to the
          analysis project.
    """
    if not (self.remote_instance_name or self.disk_names):
      self.ModuleError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)

    disks_to_copy = []

    if self.disk_names:
      disks_to_copy = self._GetDisksFromNames(self.disk_names)

    elif self.remote_instance_name:
      disks_to_copy = self._GetDisksFromInstance(self.remote_instance_name,
                                                 self.all_disks)

    if not disks_to_copy:
      self.ModuleError('Could not find any disks to copy', critical=True)
      return []

    return disks_to_copy

modules_manager.ModulesManager.RegisterModule(AzureCollector)
