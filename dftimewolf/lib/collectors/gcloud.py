# -*- coding: utf-8 -*-
"""Creates an analysis VM and copies GCP disks to it for analysis."""

from __future__ import print_function
from __future__ import unicode_literals

from googleapiclient.errors import HttpError
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import ApplicationDefaultCredentialsError
from libcloudforensics import gcp

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager


class GoogleCloudCollector(module.BaseModule):
  """Google Cloud (GCP) Collector.

  Attributes:
    analysis_project (gcp.GoogleCloudProject): project that
        contains the analysis VM.
    analysis_vm (gcp.GoogleComputeInstance): analysis VM on
         which the disk copy will be attached.
    incident_id (str): incident identifier used to name the analysis VM.
    remote_project (gcp.GoogleCloudProject): source project
        containing the VM to copy.
    remote_instance_name (gcp.GoogleComputeInstance): instance
        that needs forensicating.
    disk_names (list[str]): Comma-separated list of disk names to copy.
    incident_id (str): incident identifier on which the name of the analysis
        VM will be based.
    all_disks (bool): True if all disks attached to the source
        instance should be copied.
  """

  _ANALYSIS_VM_CONTAINER_ATTRIBUTE_NAME = 'Analysis VM'
  _ANALYSIS_VM_CONTAINER_ATTRIBUTE_TYPE = 'text'

  def __init__(self, state, critical=False):
    """Initializes a Google Cloud (GCP) collector.

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
    self.incident_id = None
    self.all_disks = False
    self._gcp_label = {}

  def Process(self):
    """Copies a disk to the analysis project."""
    for disk in self._FindDisksToCopy():
      print('Disk copy of {0:s} started...'.format(disk.name))
      snapshot = disk.snapshot()
      new_disk = self.analysis_project.create_disk_from_snapshot(
          snapshot, disk_name_prefix='incident' + self.incident_id)
      new_disk.add_labels(self._gcp_label)
      self.analysis_vm.attach_disk(new_disk)
      snapshot.delete()
      print('Disk {0:s} successfully copied to {1:s}'.format(
          disk.name, new_disk.name))
      self.state.output.append((self.analysis_vm.name, new_disk))

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(self,
            analysis_project_name,
            remote_project_name,
            incident_id,
            zone,
            boot_disk_size,
            cpu_cores,
            remote_instance_name=None,
            disk_names=None,
            all_disks=False,
            image_project='ubuntu-os-cloud',
            image_family='ubuntu-1804-lts'):
    """Sets up a Google Cloud (GCP) collector.

    This method creates and starts an analysis VM in the analysis project and
    selects disks to copy from the remote project.

    If disk_names is specified, it will copy the corresponding disks from the
    project, ignoring disks belonging to any specific instances.

    If remote_instance_name is specified, two behaviors are possible:
    * If no other parameters are specified, it will select the instance's boot
      disk
    * if all_disks is set to True, it will select all disks in the project
      that are attached to the instance

    disk_names takes precedence over instance_names

    Args:
      analysis_project_name (str): name of the project that contains
          the analysis VM.
      remote_project_name (str): name of the remote project where the disks
          must be copied from.
      incident_id (str): incident identifier on which the name of the analysis
          VM will be based.
      zone (str): GCP zone in which new resources should be created.
      boot_disk_size (float): size of the analysis VM boot disk (in GB).
      cpu_cores (int): number of CPU cores to create the VM with.
      remote_instance_name (Optional[str]): name of the instance in
          the remote project containing the disks to be copied.
      disk_names (Optional[str]): Comma separated disk names to copy.
      all_disks (Optional[bool]): True if all disks attached to the source
          instance should be copied.
      image_project (Optional[str]): name of the project where the analysis
          VM image is hosted.
      image_family (Optional[str]): name of the image to use to create the
          analysis VM.
    """
    disk_names = disk_names.split(',') if disk_names else []

    self.analysis_project = gcp.GoogleCloudProject(
        analysis_project_name, default_zone=zone)
    self.remote_project = gcp.GoogleCloudProject(
        remote_project_name)

    self.remote_instance_name = remote_instance_name
    self.disk_names = disk_names
    self.incident_id = incident_id
    self.all_disks = all_disks
    self._gcp_label = {'incident_id': self.incident_id}

    analysis_vm_name = 'gcp-forensics-vm-{0:s}'.format(self.incident_id)

    print('Your analysis VM will be: {0:s}'.format(analysis_vm_name))
    print('Complimentary gcloud command:')
    print('gcloud compute ssh --project {0:s} {1:s} --zone {2:s}'.format(
        self.analysis_project.project_id,
        analysis_vm_name,
        zone))

    self.state.StoreContainer(
        containers.TicketAttribute(
            name=self._ANALYSIS_VM_CONTAINER_ATTRIBUTE_NAME,
            type_=self._ANALYSIS_VM_CONTAINER_ATTRIBUTE_TYPE,
            value=analysis_vm_name))

    try:
      # TODO: Make creating an analysis VM optional
      # pylint: disable=too-many-function-args

      self.analysis_vm, _ = gcp.start_analysis_vm(
          self.analysis_project.project_id,
          analysis_vm_name,
          zone,
          boot_disk_size,
          int(cpu_cores),
          attach_disk=None,
          image_project=image_project,
          image_family=image_family)
      self.analysis_vm.add_labels(self._gcp_label)
      self.analysis_vm.get_boot_disk().add_labels(self._gcp_label)

    except AccessTokenRefreshError as exception:
      self.state.AddError('Something is wrong with your gcloud access token.')
      self.state.AddError(exception, critical=True)

    except ApplicationDefaultCredentialsError as exception:
      self.state.AddError(
          'Something is wrong with your Application Default Credentials. '
          'Try running:\n  $ gcloud auth application-default login')
      self.state.AddError(exception, critical=True)

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
        disks.append(self.remote_project.get_disk(name))
      except RuntimeError:
        self.state.AddError(
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
      remote_instance = self.remote_project.get_instance(instance_name)
    except RuntimeError as exception:
      self.state.AddError(str(exception), critical=True)
      return []

    if all_disks:
      return [
          self.remote_project.get_disk(disk_name)
          for disk_name in remote_instance.list_disks()
      ]
    return [remote_instance.get_boot_disk()]

  def _FindDisksToCopy(self):
    """Determines which disks to copy depending on object attributes.

    Returns:
      list[gcp.GoogleComputeDisk]: the disks to copy to the
          analysis project.
    """
    if not (self.remote_instance_name or self.disk_names):
      self.state.AddError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)
      return []

    disks_to_copy = []

    try:

      if self.disk_names:
        disks_to_copy = self._GetDisksFromNames(self.disk_names)

      elif self.remote_instance_name:
        disks_to_copy = self._GetDisksFromInstance(self.remote_instance_name,
                                                   self.all_disks)

    except HttpError as exception:
      if exception.resp.status == 403:
        self.state.AddError(
            'Make sure you have the appropriate permissions on the project')
      if exception.resp.status == 404:
        self.state.AddError(
            'GCP resource not found. Maybe a typo in the project / instance / '
            'disk name?')
      self.state.AddError(str(exception), critical=True)

    if not disks_to_copy:
      self.state.AddError(
          'Could not find any disks to copy', critical=True)

    return disks_to_copy

modules_manager.ModulesManager.RegisterModule(GoogleCloudCollector)
