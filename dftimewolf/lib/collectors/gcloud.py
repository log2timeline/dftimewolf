"""Creates a forensic VM and copies a GCP disk to it for anaysis."""

from dftimewolf.lib import module

from googleapiclient.errors import HttpError
from oauth2client.client import AccessTokenRefreshError
from turbinia.lib import libcloudforensics


class GoogleCloudCollector(module.BaseModule):
  """Class for Google Cloud Collector.

  Attributes:
    analysis_project: The project that contains the analysis VM (instance of
        libcloudforensics.GoogleCloudProject).
    analysis_vm: The analysis VM on which the disk copy will be attached
        (instance of libcloudforensics.GoogleComputeInstance).
    incident_id: The incident ID used to name the Analysis VM (string).
    disks_to_copy: A list containing the disks to copy to the analysis project
        (instances of libcloudforensics.GoogleComputeDisk).
  """

  def __init__(self, state):
    super(GoogleCloudCollector, self).__init__(state)
    self.analysis_project = None
    self.analysis_vm = None
    self.incident_id = None
    self.disks_to_copy = []

  def cleanup(self):
    pass

  def process(self):
    """Copy a disk to the analysis project.

    Returns:
      Array containing a tuple of the analysis VM's name and name of the new
      copy of the disk.
    """
    for disk in self.disks_to_copy:
      print "Disk copy of {0:s} started...".format(disk.name)
      snapshot = disk.snapshot()
      new_disk = self.analysis_project.create_disk_from_snapshot(
          snapshot, disk_name_prefix="incident" + self.incident_id)
      self.analysis_vm.attach_disk(new_disk)
      snapshot.delete()
      print "Disk {0:s} succesfully copied to {1:s}".format(
          disk.name, new_disk.name)
      self.state.output.append((self.analysis_vm.name, new_disk))

  # pylint: disable=arguments-differ
  def setup(self,
            analysis_project_name,
            remote_project_name,
            incident_id,
            zone,
            boot_disk_size,
            remote_instance_name=None,
            disk_names=None,
            all_disks=False):
    """Sets up a Google cloud collector.

    This method creates and starts an analysis VM in the analysis project and
    selects disks to copy from the remote project.

    If disk_names is specified, it will copy the corresponding disks from the
    project, ignoring disks belonging to any specific instances.

    If remote_instance_name is specified, two behaviors are possible:
      - If no other parameters are specified, it will select the instance's boot
        disk
      - if all_disks is set to True, it will select all disks in the project
        that are attached to the instance

    disk_names takes precedence over instance_names

    Args:
      analysis_project_name: The name of the project that contains the analysis
          VM (string).
      remote_project_name: The name of the remote project where the disks must
          be copied from (string).
      incident_id: The incident ID on which the name of the analysis VM will be
          based (string).
      zone: The sone in which new resources should be created (string).
      boot_disk_size: The size of the analysis VM boot disk (in GB) (float).
      remote_instance_name: The name of the instance in the remote project
          containing the disks to be copied (string).
      disk_names: Comma separated string with disk names to copy (string).
      all_disks: Copy all disks attached to the source instance (bool).
    """

    disk_names = disk_names.split(",") if disk_names else []

    self.analysis_project = libcloudforensics.GoogleCloudProject(
        analysis_project_name, default_zone=zone)
    remote_project = libcloudforensics.GoogleCloudProject(
        remote_project_name)

    if not (remote_instance_name or disk_names):
      self.state.add_error(
          "You need to specify at least an instance name or disks to copy",
          critical=True)
      return

    self.incident_id = incident_id
    analysis_vm_name = "gcp-forensics-vm-{0:s}".format(incident_id)
    print "Your analysis VM will be: {0:s}".format(analysis_vm_name)
    print "Complimentary gcloud command:"
    print "gcloud compute ssh --project {0:s} {1:s} --zone {2:s}".format(
        analysis_project_name,
        analysis_vm_name,
        zone)

    try:
      # TODO: Make creating an analysis VM optional
      self.analysis_vm, _ = libcloudforensics.start_analysis_vm(
          self.analysis_project.project_id, analysis_vm_name, zone,
          boot_disk_size)

      if disk_names:
        for name in disk_names:
          try:
            self.disks_to_copy.append(remote_project.get_disk(name))
          except RuntimeError:
            self.state.add_error(
                "Disk '{0:s}' was not found in project {1:s}".format(
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
          self.state.add_error("Could not find any disks to copy",
                               critical=True)

    except AccessTokenRefreshError as err:
      self.state.add_error("Something is wrong with your gcloud access token.")
      self.state.add_error(err, critical=True)

    except HttpError as err:
      if err.resp.status == 403:
        self.state.add_error(
            "Make sure you have the appropriate permissions on the project")
      if err.resp.status == 404:
        self.state.add_error(
            "GCP resource not found. Maybe a typo in the project / instance / "
            "disk name?")
      self.state.add_error(err, critical=True)
