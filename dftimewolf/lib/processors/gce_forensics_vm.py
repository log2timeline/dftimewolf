# -*- coding: utf-8 -*-
"""Creates an analysis VM and attaches GCP disks to it for analysis."""

from typing import List, Optional, Dict

from libcloudforensics import errors as lcf_errors
from libcloudforensics.providers.gcp import forensics as gcp_forensics
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class GCEForensicsVM(module.BaseModule):
  """Google Cloud Forensics VM creator.

  Attributes:
    project (gcp.GoogleCloudProject): Project in which to create the VM.
    analysis_vm (gcp.GoogleComputeInstance): Analysis VM on
         which the disk copy will be attached.
    incident_id (str): Incident identifier used to name the analysis VM.
    boot_disk_size (Optional[float]): Optional. Size of the analysis VM boot
        disk (in GB).
    boot_disk_type (Optional[str]): Optional. Disk type to use.
    cpu_cores (Optional[int]): Optional. Number of CPU cores to create the VM
        with.
    image_project (Optional[str]): Optional. Name of the project where the
        analysis VM image is hosted.
    image_family (Optional[str]): Optional. Name of the image to use to
        create the analysis VM.
    create_analysis_vm: Legacy option. False to skip this module entirely.
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
    super(GCEForensicsVM, self).__init__(
        state, name=name, critical=critical)
    self.project = None  # type: gcp_project.GoogleCloudProject
    self.analysis_vm = None  # type: compute.GoogleComputeInstance
    self.incident_id = str()
    self.boot_disk_size = 0.0
    self.boot_disk_type = str()
    self.cpu_cores = 0
    self.image_project = str()
    self.image_family = str()
    self._gcp_label = {}  # type: Dict[str, str]
    self.create_analysis_vm = bool()

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            project_name: str,
            incident_id: str,
            zone: str,
            boot_disk_size: float,
            boot_disk_type: str,
            cpu_cores: int,
            image_project: str,
            image_family: str,
            create_analysis_vm: bool) -> None:
    """Sets up a GCE Forensics VM processor.

    Args:
      project_name: Optional. name of the project that contains the analysis VM.
      zone: Optional. GCP zone in which new resources should be created.
      boot_disk_size: Size of the analysis VM boot disk (in GB). Default is 50.
      boot_disk_type: Disk type to use.
      cpu_cores: Number of CPU cores to create the VM with.
      image_project: Name of the project where the analysis VM image is hosted.
      image_family: Name of the image to use to create the analysis VM.
      create_analysis_vm: Legacy option. False to skip this module entirely.
    """
    self.create_analysis_vm = create_analysis_vm
    if not self.create_analysis_vm:
      self.logger.warning('Skipping SetUp for Forensics VM creation.')
      return

    self.project = gcp_project.GoogleCloudProject(
        project_name, default_zone=zone)

    if incident_id:
      self.incident_id = incident_id
      self._gcp_label = {'incident_id': self.incident_id}

    self.boot_disk_size = boot_disk_size
    self.boot_disk_type = boot_disk_type
    self.cpu_cores = cpu_cores
    self.image_project = image_project
    self.image_family = image_family

  def Process(self) -> None:
    """Launches the analysis VM."""
    if not self.create_analysis_vm:
      self.logger.warning('Skipping Process for Forensics VM creation.')
      return

    if self.incident_id:
      analysis_vm_name = f'gcp-forensics-vm-{self.incident_id}'
    else:
      analysis_vm_name = common.GenerateUniqueInstanceName(
          'gcp-forensics-vm',
          common.COMPUTE_NAME_LIMIT)
    self.logger.success(f'Your analysis VM will be: {analysis_vm_name}')
    self.logger.info('Complimentary gcloud command:')
    self.logger.info(
        f'gcloud compute ssh --project {self.project.project_id} '
        f'{analysis_vm_name} --zone {self.project.default_zone}')
    self.state.StoreContainer(
        containers.TicketAttribute(
            name=self._ANALYSIS_VM_CONTAINER_ATTRIBUTE_NAME,
            type_=self._ANALYSIS_VM_CONTAINER_ATTRIBUTE_TYPE,
            value=analysis_vm_name))
    try:
      # pylint: disable=too-many-function-args
      # pylint: disable=redundant-keyword-arg
      self.analysis_vm, created = gcp_forensics.StartAnalysisVm(
          self.project.project_id,
          analysis_vm_name,
          self.project.default_zone,
          self.boot_disk_size,
          self.boot_disk_type,
          int(self.cpu_cores),
          image_project=self.image_project,
          image_family=self.image_family)
    except lcf_errors.ResourceCreationError as exception:
      self.logger.error(f'Could not create VM: {exception}')
      self.ModuleError(str(exception), critical=True)
    if not created:
      self.logger.info(f'Instance {analysis_vm_name} exists: resusing.')
    if self._gcp_label:
      self.analysis_vm.AddLabels(self._gcp_label)
      self.analysis_vm.GetBootDisk().AddLabels(self._gcp_label)
    self.state.StoreContainer(containers.ForensicsVM(
        name=self.analysis_vm.name,
        evidence_disk=None,
        platform='gcp'))

    for d in [d.name for d in self.state.GetContainers(containers.GCEDisk)]:
      self.logger.info(f'Attaching {d} to {analysis_vm_name}')
      self.analysis_vm.AttachDisk(compute.GoogleComputeDisk(
          self.project.project_id,
          self.project.default_zone,
          d))


modules_manager.ModulesManager.RegisterModule(GCEForensicsVM)
