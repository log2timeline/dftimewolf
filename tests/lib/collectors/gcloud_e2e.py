# -*- coding: utf-8 -*-
# Copyright 2020 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""End to end test for the Google Cloud Collector."""
import json
import os
import time
import unittest
import logging

from googleapiclient.errors import HttpError
from libcloudforensics import gcp

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.collectors import gcloud

log = logging.getLogger(__name__)


class EndToEndTest(unittest.TestCase):
  """End to end test on GCP for the gcloud.py collector.

  This end-to-end test runs directly on GCP and tests that:
    1. The gcloud.py collector connects to the target instance and makes a
    snapshot of the boot disk (by default) or of the disk passed in
    parameter to the collector's SetUp method (disk_names).
    2. A new disk is created from the taken snapshot.
    3. If an analysis VM already exists, the module will attach the disk
    copy to the VM. Otherwise, it will create a new GCP instance for
    analysis purpose and attach the disk copy to it.

  To run this test, add your project information to a project_info.json file:

  {
    "project_id": "xxx", # required
    "instance": "xxx", # required
    "disk": "xxx", # optional
    "zone": "xxx" # required
  }

  Export a PROJECT_INFO environment variable with the absolute path to your
  file: "user@terminal:~$ export PROJECT_INFO='absolute/path/project_info.json'"

  """

  def __init__(self, *args, **kwargs):
    super(EndToEndTest, self).__init__(*args, **kwargs)
    try:
      project_info = ReadProjectInfo()
    except (OSError, RuntimeError, ValueError) as exception:
      self.error_msg = str(exception)
      return
    self.project_id = project_info['project_id']
    self.instance_to_analyse = project_info['instance']
    # Optional: test a disk other than the boot disk
    self.disk_to_forensic = project_info.get('disk', None)
    self.zone = project_info['zone']
    self.gcp = gcp.GoogleCloudProject(self.project_id, self.zone)

  def setUp(self):
    if hasattr(self, 'error_msg'):
      raise unittest.SkipTest(self.error_msg)
    self.incident_id = 'fake-incident-id'
    self.test_state = state.DFTimewolfState(config.Config)
    self.gcloud_collector = gcloud.GoogleCloudCollector(self.test_state)

  def test_end_to_end_boot_disk(self):
    """End to end test on GCP for the gcloud.py collector.

    This end-to-end test runs directly on GCP and tests that:
      1. The gcloud.py collector connects to the target instance and makes a
      snapshot of the boot disk.
      2. A new disk is created from the taken snapshot.
      3. If an analysis VM already exists, the module will attach the disk
      copy to the VM. Otherwise, it will create a new GCP instance for
      analysis purpose and attach the boot disk copy to it.
    """

    # Setting up the collector to make a copy of the boot disk only
    self.gcloud_collector.SetUp(
        self.project_id,
        self.project_id,
        self.incident_id,
        self.zone,
        42.0,
        'pd-standard',
        16,
        remote_instance_name=self.instance_to_analyse,
        # disk_names=None by default, boot disk will be copied
    )

    # Attach the boot disk copy to the analysis VM
    self.gcloud_collector.Process()

    # The forensic instance should be live in the analysis GCP project and
    # the disk should be attached
    analysis_vm_name = self.test_state.output[0][0]
    expected_disk_name = self.test_state.output[0][1].name

    gce_instances_client = self.gcp.GceApi().instances()
    request = gce_instances_client.get(
        project=self.project_id,
        zone=self.zone,
        instance=analysis_vm_name)
    response = request.execute()

    self.assertEqual(response['name'], analysis_vm_name)
    for disk in response['disks']:
      if disk['source'].split("/")[-1] == expected_disk_name:
        return
    self.fail('Error: could not find the disk {0:s} in instance {1:s}'.format(
        expected_disk_name, analysis_vm_name
    ))

  def test_end_to_end_other_disk(self):
    """End to end test on GCP for the gcloud.py collector.

    This end-to-end test runs directly on GCP and tests that:
      1. The gcloud.py collector connects to the target instance and makes a
      snapshot of the disk passed to the 'disk_names' parameter in the
      SetUp() method.
      2. A new disk is created from the taken snapshot.
      3. If an analysis VM already exists, the module will attach the disk
      copy to the VM. Otherwise, it will create a new GCP instance for
      analysis purpose and attach the boot disk copy to it.
    """

    # This should make a copy of the disk specified in 'disk-names'
    self.gcloud_collector.SetUp(
        self.project_id,
        self.project_id,
        self.incident_id,
        self.zone,
        42.0,
        'pd-standard',
        16,
        remote_instance_name=self.instance_to_analyse,
        disk_names=self.disk_to_forensic
    )

    # Attach the disk_to_forensic copy to the analysis VM
    self.gcloud_collector.Process()

    # The forensic instance should be live in the analysis GCP project and
    # the disk should be attached
    analysis_vm_name = self.test_state.output[0][0]
    expected_disk_name = self.test_state.output[0][1].name

    gce_instances_client = self.gcp.GceApi().instances()
    request = gce_instances_client.get(
        project=self.project_id,
        zone=self.zone,
        instance=analysis_vm_name)
    response = request.execute()

    self.assertEqual(response['name'], analysis_vm_name)
    for disk in response['disks']:
      if disk['source'].split("/")[-1] == expected_disk_name:
        return
    self.fail('Error: could not find the disk {0:s} in instance {1:s}'.format(
        expected_disk_name, analysis_vm_name
    ))

  def tearDown(self):
    CleanUp(self.project_id, self.zone, self.gcloud_collector.analysis_vm.name)


def ReadProjectInfo():
  """Read project information to run e2e test.
  Returns:
    dict: A dict with the project information.

  Raises:
    OSError: if the file cannot be found, opened or closed.
    RuntimeError: if the json file cannot be parsed.
    ValueError: if the json file does not have the required properties.
  """
  project_info = os.environ.get('PROJECT_INFO')
  if project_info is None:
    raise OSError('Error: please make sure that you defined the '
                  '"PROJECT_INFO" environment variable pointing '
                  'to your project settings.')
  try:
    json_file = open(project_info)
    try:
      project_info = json.load(json_file)
    except ValueError as exception:
      raise RuntimeError('Error: cannot parse JSON file. {0:s}'.format(
          str(exception)))
    json_file.close()
  except OSError as exception:
    raise OSError('Error: could not open/close file {0:s}: {1:s}'.format(
        project_info, str(exception)
    ))

  if not all(key in project_info for key in ['project_id', 'instance',
                                             'zone']):
    raise ValueError('Error: please make sure that your JSON file '
                     'has the required entries. The file should '
                     'contain at least the following: ["project_id", '
                     '"instance", "zone"].')

  return project_info


def CleanUp(project_id, zone, instance_name):
  """Clean up GCP project.

  Remove the instance [instance_name] in the GCP project [project_id] and its
  disks that were created as part of the end to end test.

  Attributes:
    project_id (str): the project id of the GCP project.
    zone (str): the zone for the project.
    instance_name (str): the name of the analysis VM to remove.
  """

  gcp_project = gcp.GoogleCloudProject(project_id, zone)
  disks = gcp.GoogleComputeInstance(
      gcp_project, zone, instance_name).ListDisks()

  # delete the created forensics VMs
  log.info('Deleting analysis instance: {0:s}.'.format(instance_name))
  gce_instances_client = gcp_project.GceApi().instances()
  request = gce_instances_client.delete(
      project=gcp_project.project_id,
      zone=gcp_project.default_zone,
      instance=instance_name
  )
  try:
    request.execute()
  except HttpError:
    # GceOperation triggers a while(True) loop that checks on the
    # operation ID. Sometimes it loops one more time right when the
    # operation has finished and thus the associated ID doesn't exists
    # anymore, throwing an HttpError. We can ignore this.
    pass
  log.info('Instance {0:s} successfully deleted.'.format(instance_name))

  # delete the copied disks
  # we ignore the disk that was created for the analysis VM (disks[0]) as
  # it is deleted in the previous operation
  gce_disks_client = gcp_project.GceApi().disks()
  for disk in disks[1:]:
    log.info('Deleting disk: {0:s}.'.format(disk))
    while True:
      try:
        request = gce_disks_client.delete(
            project=gcp_project.project_id,
            zone=gcp_project.default_zone,
            disk=disk
        )
        request.execute()
        break
      except HttpError as exception:
        # GceApi() will throw a 400 error until the analysis VM deletion is
        # correctly propagated. When the disk is finally deleted, it will
        # throw a 404 not found if it looped again after deletion.
        if exception.resp.status == 404:
          break
        if exception.resp.status != 400:
          log.warning('Could not delete the disk {0:s}: {1:s}'.format(
              disk, str(exception)
          ))
        # Throttle the requests to one every 10 seconds
        time.sleep(10)

    log.info('Disk {0:s} successfully deleted.'.format(
        disk))


if __name__ == '__main__':
  unittest.main()
