# -*- coding: utf-8 -*-
"""Creates an analysis VM and copies AWS volumes to it for analysis."""

from typing import List, Optional

from libcloudforensics.providers.aws import forensics as aws_forensics
from libcloudforensics.providers.aws.internal import account as aws_account
from libcloudforensics.providers.aws.internal import ebs
from libcloudforensics.providers.aws.internal import ec2  # pylint: disable=unused-import,line-too-long  # used in typing

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class AWSCollector(module.BaseModule):
  """Amazon Web Services (AWS) Collector.

  Attributes:
    remote_profile_name (str): The AWS account in which the volume(s) exist(s).
        This is the profile name that is defined in your AWS credentials file.
    remote_zone (str): The AWS zone in which the source volume(s) exist(s).
    source_account (AWSAccount): The AWSAccount object that represents the
        source account in which the volume(s) exist(s).
    incident_id (str): Incident identifier used to name the analysis VM.
    remote_instance_id (str): Instance ID that needs forensicating.
    volume_ids (list[str]): List of volume IDs to copy.
    all_volumes (bool): True if all volumes attached to the source
        instance should be copied.
    analysis_profile_name (str): The AWS account in which to create the
        analysis VM. This is the profile name that is defined in your AWS
        credentials file.
    analysis_zone (str): The AWS zone in which to create the VM.
    analysis_vm (AWSInstance): Analysis VM to which the volume copy will be
        attached.
    device_names (list[str]): A list of available device names to be
        used by AWS to attach volumes to the analysis VM.
  """

  _ANALYSIS_VM_CONTAINER_ATTRIBUTE_NAME = 'Analysis VM'
  _ANALYSIS_VM_CONTAINER_ATTRIBUTE_TYPE = 'text'

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes an Amazon Web Services (AWS) collector.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(AWSCollector, self).__init__(state, name=name, critical=critical)
    self.remote_profile_name = str()
    self.remote_zone = str()
    self.source_account = None  # type: aws_account.AWSAccount
    self.incident_id = str()
    self.remote_instance_id = None  # type: Optional[str]
    self.volume_ids = []  # type: List[str]
    self.all_volumes = False
    self.analysis_profile_name = None  # type: Optional[str]
    self.analysis_zone = None  # type: Optional[str]
    self.analysis_vm = None  # type: ec2.AWSInstance
    # See https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/device_naming.html
    self.device_suffixes = list('fghijklmnop')

  def Process(self) -> None:
    """Copies a volume and attaches it to the analysis VM."""
    for volume in self._FindVolumesToCopy():
      self.logger.info(f'Volume copy of {volume.volume_id} started...')
      new_volume = aws_forensics.CreateVolumeCopy(
          self.remote_zone,
          dst_zone=self.analysis_zone,
          volume_id=volume.volume_id,
          src_profile=self.remote_profile_name,
          dst_profile=self.analysis_profile_name)
      self.analysis_vm.AttachVolume(
          new_volume, self._FindNextAvailableDeviceName())
      self.logger.info(f'Volume {volume.volume_id} successfully copied to '
          f'{new_volume.volume_id}')

      container = containers.ForensicsVM(
          name=self.analysis_vm.name,
          evidence_disk=new_volume,
          platform='aws')
      self.state.StoreContainer(container)

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            remote_profile_name: str,
            remote_zone: str,
            incident_id: str,
            remote_instance_id: Optional[str]=None,
            volume_ids: Optional[str]=None,
            all_volumes: bool=False,
            analysis_profile_name: Optional[str]=None,
            analysis_zone: Optional[str]=None,
            boot_volume_size: int=50,
            cpu_cores: int=16,
            ami: None=None) -> None:
    """Sets up an Amazon web Services (AWS) collector.

    This method creates and starts an analysis VM in the AWS account and
    selects volumes to copy from the target instance / list of volumes passed
    in parameter.

    If volume_ids is specified, it will copy the corresponding volumes from the
    account, ignoring volumes belonging to any specific instances.

    If remote_instance_id is specified, two behaviors are possible:
    * If no other parameters are specified, it will select the instance's boot
      volume.
    * if all_volumes is set to True, it will select all volumes in the account
      that are attached to the instance.

    volume_ids takes precedence over remote_instance_id.

    Args:
      remote_profile_name (str): The AWS account in which the
          volume(s) exist(s). This is the profile name that is defined in
          your AWS credentials file.
      remote_zone (str): The AWS zone in which the source volume(s) exist(s).
      incident_id (str): Incident identifier used to name the analysis VM.
      remote_instance_id (str): Optional. Instance ID that needs forensicating.
      volume_ids (str): Optional. Comma-separated list of volume ids to
          copy.
      all_volumes (bool): Optional. True if all volumes attached to the source
          instance should be copied.
      analysis_profile_name (str): Optional. The AWS account in which to
          create the analysis VM. This is the profile name that is defined in
          your AWS credentials file.
      analysis_zone (str): Optional. The AWS zone in which to create the VM.
          If not specified, the VM will be created in the same zone where the
          volume(s) exist(s).
      boot_volume_size (int): Optional. The size (in GB) of the boot volume
          for the analysis VM. Default is 50 GB.
      cpu_cores (int): Optional. The number of CPU cores to use for the
          analysis VM. Default is 16.
      ami (str): Optional. The Amazon Machine Image ID to use to create the
          analysis VM. If not specified, will default to selecting Ubuntu 18.04
          TLS.
    """

    if not (remote_instance_id or volume_ids):
      self.ModuleError(
          'You need to specify at least an instance name or volume ids to copy',
          critical=True)
      return

    if not (remote_profile_name and remote_zone):
      self.ModuleError('You must specify "remote_profile_name" and "zone" '
                       'parameters', critical=True)
      return

    self.remote_profile_name = remote_profile_name
    self.remote_zone = remote_zone
    self.source_account = aws_account.AWSAccount(
        self.remote_zone, aws_profile=self.remote_profile_name)

    self.incident_id = incident_id
    self.remote_instance_id = remote_instance_id

    self.volume_ids = volume_ids.split(',') if volume_ids else []
    self.all_volumes = all_volumes
    self.analysis_zone = analysis_zone or remote_zone
    self.analysis_profile_name = analysis_profile_name or remote_profile_name

    analysis_vm_name = f'aws-forensics-vm-{self.incident_id}'
    self.logger.info(f'Your analysis VM will be: {analysis_vm_name}')
    self.state.StoreContainer(
        containers.TicketAttribute(
            name=self._ANALYSIS_VM_CONTAINER_ATTRIBUTE_NAME,
            type_=self._ANALYSIS_VM_CONTAINER_ATTRIBUTE_TYPE,
            value=analysis_vm_name))
    self.analysis_vm, _ = aws_forensics.StartAnalysisVm(
        analysis_vm_name,
        self.analysis_zone,
        boot_volume_size,
        ami=ami,
        cpu_cores=cpu_cores,
        dst_profile=self.analysis_profile_name,
    )

  def _GetVolumesFromIds(self, volume_ids: List[str]) -> List[ebs.AWSVolume]:
    """Gets volumes from an account by volume IDs.

    Args:
      volume_ids (list[str]): List of volume ids to get from the account.

    Returns:
      list[ebs.AWSVolume]: List of ebs.AWSVolume objects to copy.
    """
    volumes = []
    for volume_id in volume_ids:
      try:
        volumes.append(self.source_account.ebs.GetVolumeById(volume_id))
      except RuntimeError:
        self.ModuleError(f'Volume "{volume_id}" was not found in AWS account '
                f'{self.remote_profile_name}',
            critical=True)
        return []
    return volumes

  def _GetVolumesFromInstance(self,
                              instance_id: str,
                              all_volumes: bool) -> List[ebs.AWSVolume]:
    """Gets volumes to copy based on an instance name.

    Args:
      instance_id (str): Instance ID of the instance to get the volumes from.
      all_volumes (bool): If True, get all volumes attached to the instance. If
          False, get only the instance's boot volume.

    Returns:
      list[ebs.AWSVolume]: List of ebs.AWSVolume objects to copy.
    """
    try:
      remote_instance = self.source_account.ec2.GetInstanceById(instance_id)
    except RuntimeError as exception:
      self.ModuleError(str(exception), critical=True)
      return []

    if all_volumes:
      return list(remote_instance.ListVolumes().values())
    return [remote_instance.GetBootVolume()]

  def _FindVolumesToCopy(self) -> List[ebs.AWSVolume]:
    """Determines which volumes to copy depending on the collector's attributes.

    Returns:
      list[ebs.AWSVolume]: A list of the volumes to copy.
    """

    volumes_to_copy = []
    if self.volume_ids:
      volumes_to_copy = self._GetVolumesFromIds(self.volume_ids)
    elif self.remote_instance_id:
      volumes_to_copy = self._GetVolumesFromInstance(self.remote_instance_id,
                                                     self.all_volumes)

    if not volumes_to_copy:
      self.ModuleError(
          'Could not find any volumes to copy', critical=True)
      return []

    return volumes_to_copy

  def _FindNextAvailableDeviceName(self) -> str:
    """Determine the next available device name to attach volumes to the VM.

    AWS recommends using device names that are within /dev/sd[f-p][1-6].

    Returns:
      str: A device name, or an empty string if a name could not be obtained.
    """
    try:
      next_available = self.device_suffixes.pop(0)
    except IndexError as exception:
      self.ModuleError('Error: there are no more device names available '
                       'for this VM. Consider copying less volumes! '
                       f'{str(exception)}', critical=True)
      return ''
    return '/dev/sd' + next_available


modules_manager.ModulesManager.RegisterModule(AWSCollector)
