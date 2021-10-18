# -*- coding: utf-8 -*-
"""Classes for storing GCP disks into containers."""

from typing import List, Optional, Dict
from typing import Set

from google.auth.exceptions import DefaultCredentialsError, RefreshError
from googleapiclient.errors import HttpError
from libcloudforensics.errors import ResourceNotFoundError
from libcloudforensics.providers.gcp import forensics as gcp_forensics
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import gke
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import compute

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class GCEDiskCopier(module.BaseModule):
  """Google Cloud Platform (GCP) disk copier.

  Attributes:
    analysis_project (gcp.GoogleCloudProject): Project that
        contains the analysis VM.
    analysis_vm (gcp.GoogleComputeInstance): Analysis VM on
         which the disk copy will be attached.
    incident_id (str): Incident identifier used to name the analysis VM.
    remote_project (gcp.GoogleCloudProject): Source project
        containing the VM to copy.
    incident_id (str): Incident identifier on which the name of the analysis
        VM will be based.
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
    super(GCEDiskCopier, self).__init__(
        state, name=name, critical=critical)
    self.analysis_project = None  # type: gcp_project.GoogleCloudProject
    self.analysis_vm = None  # type: compute.GoogleComputeInstance
    self.incident_id = str()
    self.remote_project = None  # type: gcp_project.GoogleCloudProject
    self._gcp_label = {}  # type: Dict[str, str]

  def Process(self) -> None:
    """Copies a disk to the analysis project."""
    for disk in self.state.GetContainers(containers.GCEDisk):
      self.logger.info('Disk copy of {0:s} started...'.format(disk.name))
      new_disk = gcp_forensics.CreateDiskCopy(
          self.remote_project.project_id,
          self.analysis_project.project_id,
          self.analysis_project.default_zone,
          disk_name=disk.name)
      self.logger.success('Disk {0:s} successfully copied to {1:s}'.format(
          disk.name, new_disk.name))
      if self._gcp_label:
        new_disk.AddLabels(self._gcp_label)
      self.analysis_vm.AttachDisk(new_disk)

      container = containers.ForensicsVM(
          name=self.analysis_vm.name,
          evidence_disk=new_disk,
          platform='gcp')
      self.state.StoreContainer(container)

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            analysis_project_name: str,
            remote_project_name: str,
            incident_id: Optional[str]=None,
            zone: str='us-central1-f',
            create_analysis_vm: bool=True,
            boot_disk_size: float=50,
            boot_disk_type: str='pd-standard',
            cpu_cores: int=4,
            image_project: str='ubuntu-os-cloud',
            image_family: str='ubuntu-1804-lts') -> None:
    """Sets up a Google Cloud Platform(GCP) collector.

    This method creates and starts an analysis VM in the analysis project and
    selects disks to copy from the remote project.

    If analysis_project_name is not specified, analysis_project will be same
    as remote_project.

    If disk_names is specified, it will copy the corresponding disks from the
    project, ignoring disks belonging to any specific instances.

    If remote_instance_name is specified, two behaviors are possible:
    * If no other parameters are specified, it will select the instance's boot
      disk
    * if all_disks is set to True, it will select all disks in the project
      that are attached to the instance

    disk_names takes precedence over instance_names

    Args:
      analysis_project_name (str): Optional. name of the project that contains
          the analysis VM. Default is None.
      remote_project_name (str): name of the remote project where the disks
          must be copied from.
      incident_id (Optional[str]): Optional. Incident identifier on which the
          name of the analysis VM will be based. Default is None, which means
          add no label and format VM name as
          "gcp-forensics-vm-{TIMESTAMP('%Y%m%d%H%M%S')}".
      zone (Optional[str]): Optional. GCP zone in which new resources should
          be created. Default is us-central1-f.
      create_analysis_vm (Optional[bool]): Optional. Create analysis VM in
          the analysis project. Default is True.
      boot_disk_size (Optional[float]): Optional. Size of the analysis VM boot
          disk (in GB). Default is 50.
      boot_disk_type (Optional[str]): Optional. Disk type to use.
          Default is pd-standard.
      cpu_cores (Optional[int]): Optional. Number of CPU cores to
          create the VM with. Default is 4.
      image_project (Optional[str]): Optional. Name of the project where the
          analysis VM image is hosted.
      image_family (Optional[str]): Optional. Name of the image to use to
          create the analysis VM.
    """
    self.remote_project = gcp_project.GoogleCloudProject(
        remote_project_name, default_zone=zone)
    if analysis_project_name:
      self.analysis_project = gcp_project.GoogleCloudProject(
          analysis_project_name, default_zone=zone)
    else:
      self.analysis_project = self.remote_project

    if incident_id:
      self.incident_id = incident_id
      self._gcp_label = {'incident_id': self.incident_id}

    if create_analysis_vm:
      if self.incident_id:
        analysis_vm_name = 'gcp-forensics-vm-{0:s}'.format(self.incident_id)
      else:
        analysis_vm_name = common.GenerateUniqueInstanceName(
            'gcp-forensics-vm',
            common.COMPUTE_NAME_LIMIT)

      self.logger.success('Your analysis VM will be: {0:s}'.format(
          analysis_vm_name))
      self.logger.info('Complimentary gcloud command:')
      self.logger.info(
          'gcloud compute ssh --project {0:s} {1:s} --zone {2:s}'.format(
              self.analysis_project.project_id,
              analysis_vm_name,
              self.analysis_project.default_zone))

      self.state.StoreContainer(
          containers.TicketAttribute(
              name=self._ANALYSIS_VM_CONTAINER_ATTRIBUTE_NAME,
              type_=self._ANALYSIS_VM_CONTAINER_ATTRIBUTE_TYPE,
              value=analysis_vm_name))

      try:
        # pylint: disable=too-many-function-args
        # pylint: disable=redundant-keyword-arg
        self.analysis_vm, _ = gcp_forensics.StartAnalysisVm(
            self.analysis_project.project_id,
            analysis_vm_name,
            self.analysis_project.default_zone,
            boot_disk_size,
            boot_disk_type,
            int(cpu_cores),
            image_project=image_project,
            image_family=image_family)
        if self._gcp_label:
          self.analysis_vm.AddLabels(self._gcp_label)
          self.analysis_vm.GetBootDisk().AddLabels(self._gcp_label)

      except (RefreshError, DefaultCredentialsError) as exception:
        msg = ('Something is wrong with your Application Default Credentials. '
               'Try running:\n  $ gcloud auth application-default login\n')
        msg += str(exception)
        self.ModuleError(msg, critical=True)

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

class GKEDiskCollector(module.BaseModule):

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str] = None,
               critical: Optional[bool] = False):
    """Initializes a GKE disk collector.

    Args:
      state (DFTimewolfState): Recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GKEDiskCollector, self).__init__(state, name=name, critical=critical)
    self.instances = []  # type: List[compute.GoogleComputeInstance]

  def Process(self) -> None:
    """Stores the queued instance disks into this object's state."""
    for instance in self.instances:
      disk = instance.GetBootDisk()
      self.state.StoreContainer(containers.GCEDisk(disk.name))

  def SetUp(self,
            project_name: str,
            cluster_name: str,
            cluster_zone: str,
            workload_name: Optional[str],
            workload_namespace: Optional[str]) -> None:
    """Sets up the GKE disk collector.

    This method adds instances whose disks to copy to this object's empty
    instance list. If workload details have been supplied, only the nodes
    covered by that workload will be queued.

    Args:
      project_name (str): The project ID where the cluster is to be found.
      cluster_name (str): The name of the cluster.
      cluster_zone (str): The zone of the cluster (control plane zone).
      workload_name (str): The name of the Kubernetes workload to consider.
      workload_namespace (str): The namespace of the Kubernetes workload.
    """
    project = gcp_project.GoogleCloudProject(project_name)
    cluster = gke.GkeCluster(project_name, cluster_zone, cluster_name)

    if workload_name and workload_namespace:
      # Workload name and namespace was specified, select nodes from the
      # cluster's workload
      workload = cluster.FindWorkload(workload_name, workload_namespace)
      if not workload:
        self.ModuleError('Workload not found.', critical=True)
        return
      nodes = workload.GetCoveredNodes()
    elif workload_name or workload_namespace:
      # Either workload name or workload namespace was given
      self.ModuleError(
          'Both the workload name and namespace must be supplied.',
           critical=True)
      return
    else:
      # Nothing about a workload was specified, handle the whole cluster
      nodes = cluster.ListNodes()

    for node in nodes:
      self.instances.append(project.compute.GetInstance(node.name))


modules_manager.ModulesManager.RegisterModule(GCEDiskCopier)
modules_manager.ModulesManager.RegisterModule(GCEDiskCollector)
modules_manager.ModulesManager.RegisterModule(GKEDiskCollector)
