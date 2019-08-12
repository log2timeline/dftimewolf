# -*- coding: utf-8 -*-
"""Creates an analysis VM and copies GCP disks to it for analysis."""

from __future__ import print_function
from __future__ import unicode_literals

from googleapiclient.errors import HttpError
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import ApplicationDefaultCredentialsError
from turbinia.lib import libcloudforensics

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class GoogleCloudCollector(module.BaseModule):
  """Google Cloud (GCP) Collector.

  Attributes:
    analysis_project (libcloudforensics.GoogleCloudProject): project that
        contains the analysis VM.
    analysis_vm (libcloudforensics.GoogleComputeInstance): analysis VM on
         which the disk copy will be attached.
    incident_id (str): incident identifier used to name the analysis VM.
    disks_to_copy (list[libcloudforensics.GoogleComputeDisk]): the disks
        to copy to the analysis project.
  """

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
    self.disks_to_copy = []

  def Process(self):
    """Copies a disk to the analysis project."""
    for disk in self.disks_to_copy:
      print('Disk copy of {0:s} started...'.format(disk.name))
      snapshot = disk.snapshot()
      new_disk = self.analysis_project.create_disk_from_snapshot(
          snapshot, disk_name_prefix='incident' + self.incident_id)
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

    self.analysis_project = libcloudforensics.GoogleCloudProject(
        analysis_project_name, default_zone=zone)
    remote_project = libcloudforensics.GoogleCloudProject(
        remote_project_name)

    if not (remote_instance_name or disk_names):
      self.state.AddError(
          'You need to specify at least an instance name or disks to copy',
          critical=True)
      return

    self.incident_id = incident_id
    analysis_vm_name = 'gcp-forensics-vm-{0:s}'.format(incident_id)
    print('Your analysis VM will be: {0:s}'.format(analysis_vm_name))
    print('Complimentary gcloud command:')
    print('gcloud compute ssh --project {0:s} {1:s} --zone {2:s}'.format(
        analysis_project_name,
        analysis_vm_name,
        zone))

    try:
      # TODO: Make creating an analysis VM optional
      # pylint: disable=too-many-function-args
      self.analysis_vm, _ = libcloudforensics.start_analysis_vm(
          self.analysis_project.project_id,
          analysis_vm_name,
          zone,
          boot_disk_size,
          int(cpu_cores),
          attach_disk=None,
          image_project=image_project,
          image_family=image_family)

      if disk_names:
        for name in disk_names:
          try:
            self.disks_to_copy.append(remote_project.get_disk(name))
          except RuntimeError:
            self.state.AddError(
                'Disk "{0:s}" was not found in project {1:s}'.format(
                    name, remote_project_name),
                critical=True)
            break

      elif remote_instance_name:
        remote_instance = remote_project.get_instance(
            remote_instance_name)

        if all_disks:
          self.disks_to_copy = [
              remote_project.get_disk(disk_name)
              for disk_name in remote_instance.list_disks()
          ]
        else:
          self.disks_to_copy = [remote_instance.get_boot_disk()]

        if not self.disks_to_copy:
          self.state.AddError(
              'Could not find any disks to copy', critical=True)

    except AccessTokenRefreshError as err:
      self.state.AddError('Something is wrong with your gcloud access token.')
      self.state.AddError(err, critical=True)

    except ApplicationDefaultCredentialsError as err:
      self.state.AddError(
          'Something is wrong with your Application Default Credentials. '
          'Try running:\n  $ gcloud auth application-default login')
      self.state.AddError(err, critical=True)

    except HttpError as err:
      if err.resp.status == 403:
        self.state.AddError(
            'Make sure you have the appropriate permissions on the project')
      if err.resp.status == 404:
        self.state.AddError(
            'GCP resource not found. Maybe a typo in the project / instance / '
            'disk name?')
      self.state.AddError(err, critical=True)


modules_manager.ModulesManager.RegisterModule(GoogleCloudCollector)
