# -*- coding: utf-8 -*-
"""Creates an analysis VM and copies GCP disks to it for analysis."""

from google.auth.exceptions import DefaultCredentialsError, RefreshError
from googleapiclient.errors import HttpError
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp import forensics as gcp_forensics

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager


class GoogleCloudCollector(module.BaseModule):
  """Google Cloud Platform (GCP) Collector.

  Attributes:
    analysis_project (gcp.GoogleCloudProject): Project that
        contains the analysis VM.
    analysis_vm (gcp.GoogleComputeInstance): Analysis VM on
         which the disk copy will be attached.
    incident_id (str): Incident identifier used to name the analysis VM.
    remote_project (gcp.GoogleCloudProject): Source project
        containing the VM to copy.
    remote_instance_name (str): Instance that needs forensicating.
    disk_names (list[str]): Comma-separated list of disk names to copy.
    incident_id (str): Incident identifier on which the name of the analysis
        VM will be based.
    all_disks (bool): True if all disks attached to the source
        instance should be copied.
  """

  _ANALYSIS_VM_CONTAINER_ATTRIBUTE_NAME = 'Analysis VM'
  _ANALYSIS_VM_CONTAINER_ATTRIBUTE_TYPE = 'text'

  def __init__(self, state, critical=False):
    """Initializes a Google Cloud Platform (GCP) collector.

    Args:
      state (DFTimewolfState): recipe state.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GoogleCloudCollector, self).__init__(state, critical=critical)
    self.analysis_project = None
    self.analysis_vm = None
    self.incident_id = None
    self.remote_project = None
    self.remote_instance_name = None
    self.disk_names = []
    self.all_disks = False
    self._gcp_label = {}

  def Process(self):
    """Copies a disk to the analysis project."""
    for disk in self._FindDisksToCopy():
      self.logger.info('Disk copy of {0:s} started...'.format(disk.name))
      new_disk = gcp_forensics.CreateDiskCopy(
          self.remote_project.project_id,
          self.analysis_project.project_id,
          self.analysis_project.default_zone,
          disk_name=disk.name)
      self.logger.info('Disk {0:s} successfully copied to {1:s}'.format(
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
            analysis_project_name,
            remote_project_name,
            incident_id=None,
            zone='us-central1-f',
            create_analysis_vm=True,
            boot_disk_size=50,
            boot_disk_type='pd-standard',
            cpu_cores=4,
            remote_instance_name=None,
            disk_names=None,
            all_disks=False,
            image_project=None,
            image_family=None):
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
      remote_instance_name (Optional[str]): Optional. Name of the instance in
          the remote project containing the disks to be copied.
      disk_names (Optional[str]): Optional. Comma separated disk names to copy.
      all_disks (Optional[bool]): Optional. True if all disks attached to the
          source instance should be copied.
      image_project (Optional[str]): Optional. Name of the project where the
          analysis VM image is hosted.
      image_family (Optional[str]): Optional. Name of the image to use to
          create the analysis VM.
    """
    if not (remote_instance_name or disk_names):
      self.state.AddError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)
      return

    disk_names = disk_names.split(',') if disk_names else []
    self.remote_project = gcp_project.GoogleCloudProject(
        remote_project_name, default_zone=zone)
    if analysis_project_name:
      self.analysis_project = gcp_project.GoogleCloudProject(
          analysis_project_name, default_zone=zone)
    else:
      self.analysis_project = self.remote_project

    self.remote_instance_name = remote_instance_name
    self.disk_names = disk_names
    self.all_disks = all_disks
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

      self.logger.info('Your analysis VM will be: {0:s}'.format(
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

  def _GetDisksFromNames(self, disk_names):
    """Gets disks from a project by disk name.

    Args:
      disk_names (list[str]): List of disk names to get from the project.

    Returns:
      list[GoogleComputeDisk]: List of GoogleComputeDisk objects to copy.
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
      remote_instance = self.remote_project.compute.GetInstance(instance_name)
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

modules_manager.ModulesManager.RegisterModule(GoogleCloudCollector)
