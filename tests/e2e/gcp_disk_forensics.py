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
"""End to end test for the Google Cloud Disk Forensics modules."""
import json
import logging
import os
import time
import unittest
import warnings

from googleapiclient.errors import HttpError
from libcloudforensics.providers.gcp.internal import compute, common
from libcloudforensics.providers.gcp.internal import project as gcp_project

from dftimewolf import config
from dftimewolf.lib import resources, state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.recipes import manager as recipes_manager


log = logging.getLogger(__name__)

# pylint: disable=line-too-long
RECIPE = {
    'name': 'unittest_gce_forensics_recipe',
    'short_description': 'Nothing to see here.',
    'preflights': [
        {
            'wants': [],
            'name': 'GCPTokenCheck',
            'runtime_name': 'GCPTokenCheck-destination',
            'args': {
                'project_name': '@destination_project_name'
            },
        }, {
            'wants': [],
            'name': 'GCPTokenCheck',
            'runtime_name': 'GCPTokenCheck-source',
            'args': {
                'project_name': '@source_project_name'
            },
        }
    ],
    'modules': [
        {
            'wants': [],
            'name': 'GCEDiskCopy',
            'args': {
                'source_project_name': '@source_project_name',
                'destination_project_name': '@destination_project_name',
                'disk_names': '@disks',
                'remote_instance_names': '@instances',
                'all_disks': '@all_disks',
                'destination_zone': '@zone',
                'stop_instances': '@stop_instances',
            }
        }, {
            'wants': ['GCEDiskCopy'],
            'name': 'GCEForensicsVM',
            'args': {
                'project_name': '@destination_project_name',
                'incident_id': '@incident_id',
                'zone': '@zone',
                'boot_disk_size': 50,
                'boot_disk_type': 'pd-standard',
                'cpu_cores': 4,
                'image_project': 'ubuntu-os-cloud',
                'image_family': 'ubuntu-1804-lts',
                'create_analysis_vm': True,
            }
        }
    ],
    'args': [
        ['source_project_name', 'Name of the project containing the instance / disks to copy.', None],
        ['destination_project_name', 'Name of the project where the analysis VM will be created and disks copied to.', None],
        ['--incident_id', 'Incident ID to label the VM with.', None],
        ['--instances', 'Name of the instance to analyze.', None],
        ['--disks', 'Comma-separated list of disks to copy from the source GCP project (if `instance` not provided).', None],
        ['--all_disks', 'Copy all disks in the designated instance. Overrides `disk_names` if specified.', False],
        ['--stop_instances', 'Stop the designated instance after copying disks.', False],
        ['--zone', 'The GCP zone where the Analysis VM and copied disks will be created.', 'us-central1-f']
    ]
}
# pylint: enable=line-too-long

TEST_MODULES = {
  'GCEDiskCopy': 'dftimewolf.lib.collectors.gce_disk_copy',
  'GCEForensicsVM': 'dftimewolf.lib.processors.gce_forensics_vm',
  'GCPTokenCheck': 'dftimewolf.lib.preflights.cloud_token'
}


class GCEForensicsEndToEndTest(unittest.TestCase):
  """End to end test on GCP for the gcloud.py collector.

  This end-to-end test runs directly on GCP and tests that:
    1. The GCEDiskCopy module correctly copies disks
    2. The GCEForensicsVM module correctly launches a forensics VM
    3. The disks from the first module are attached to the VM

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
    super(GCEForensicsEndToEndTest, self).__init__(*args, **kwargs)
    try:
      project_info = ReadProjectInfo()
    except (OSError, RuntimeError, ValueError) as exception:
      self.error_msg = str(exception)
      return

    self.project_id = project_info['project_id']
    self.instance_to_analyse = project_info['instance']
    # Optional: test a disk other than the boot disk
    self.disk_to_forensicate = project_info.get('disk', None)
    self.zone = project_info['zone']

  def setUp(self):
    self.incident_id = 'fake-incident-id'

    self.test_state = state.DFTimewolfState(config.Config)
    self._recipe = resources.Recipe("E2E Test Recipe", RECIPE, [])
    self._recipes_manager = recipes_manager.RecipesManager()
    self._recipes_manager.RegisterRecipe(self._recipe)

    self.gcp_client = common.GoogleCloudComputeClient(
        project_id=self.project_id)

  def tearDown(self):
    log.info("Cleaning up after test...")
    for vm in self.test_state.GetContainers(containers.ForensicsVM):
      CleanUp(self.project_id, self.zone, vm.name)

    self._recipes_manager.DeregisterRecipe(self._recipe)

  def testBootDiskCopy(self):
    """Tests copy on boot disk from an instance only."""
    warnings.filterwarnings(
        action="ignore", message="unclosed", category=ResourceWarning)

    # Load the recipe, set the arguments, and run
    self.test_state.LoadRecipe(RECIPE, TEST_MODULES)
    self.test_state.command_line_options = {
      'source_project_name': self.project_id,
      'destination_project_name': self.project_id,
      'incident_id': self.incident_id,
      'disks': None,
      'instances': self.instance_to_analyse,
      'all_disks': False,
      'zone': self.zone,
      'stop_instances': False
    }
    self.test_state.SetupModules()
    self.test_state.RunModules()

    # Get the forensics VM name, confirm it exists
    self.assertEqual(1,
        len(self.test_state.GetContainers(containers.ForensicsVM)))
    for_vm = self.test_state.GetContainers(containers.ForensicsVM)[0]

    gce_instances_client = self.gcp_client.GceApi().instances()
    request = gce_instances_client.get(
        project=self.project_id,
        zone=self.zone,
        instance=for_vm.name)
    request.execute()  # Throws exception if not found.

    # Check the disks are attached as expected
    actual_disks = compute.GoogleComputeInstance(
      self.project_id, self.zone, for_vm.name).ListDisks().keys()
    expected_disks = self.test_state.GetContainers(containers.GCEDisk)

    # Length should differ by 1 for the boot disk
    self.assertEqual(len(actual_disks), len(expected_disks) + 1)
    for d in expected_disks:
      self.assertIn(d.name, actual_disks)

  def testOtherDiskCopy(self):
    """Tests copy from a specified disk."""
    warnings.filterwarnings(
        action="ignore", message="unclosed", category=ResourceWarning)

    if not self.disk_to_forensicate:
      raise unittest.SkipTest("Disk not specified in config.")

    # Load the recipe, set the arguments, and run
    self.test_state.LoadRecipe(RECIPE, TEST_MODULES)
    self.test_state.command_line_options = {
      'source_project_name': self.project_id,
      'destination_project_name': self.project_id,
      'incident_id': self.incident_id,
      'disks': self.disk_to_forensicate,
      'instances': None,
      'all_disks': False,
      'zone': self.zone,
      'stop_instances': False
    }
    self.test_state.SetupModules()
    self.test_state.RunModules()

    # Get the forensics VM name, confirm it exists
    self.assertEqual(1,
        len(self.test_state.GetContainers(containers.ForensicsVM)))
    for_vm = self.test_state.GetContainers(containers.ForensicsVM)[0]

    gce_instances_client = self.gcp_client.GceApi().instances()
    request = gce_instances_client.get(
        project=self.project_id,
        zone=self.zone,
        instance=for_vm.name)
    request.execute()  # Throws exception if not found.

    # Check the disks are attached as expected
    actual_disks = compute.GoogleComputeInstance(
      self.project_id, self.zone, for_vm.name).ListDisks().keys()
    expected_disks = self.test_state.GetContainers(containers.GCEDisk)

    # Length should differ by 1 for the boot disk
    self.assertEqual(len(actual_disks), len(expected_disks) + 1)
    for d in expected_disks:
      self.assertIn(d.name, actual_disks)


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
          str(exception))) from ValueError
    json_file.close()
  except OSError as exception:
    raise OSError('Error: could not open/close file {0:s}: {1:s}'.format(
        project_info, str(exception)
    )) from OSError

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

  gcp_client = common.GoogleCloudComputeClient(project_id=project_id)
  project = gcp_project.GoogleCloudProject(project_id, zone)
  disks = compute.GoogleComputeInstance(
      project.project_id, zone, instance_name).ListDisks()

  # delete the created forensics VMs
  log.info('Deleting analysis instance: {0:s}.'.format(instance_name))
  gce_instances_client = gcp_client.GceApi().instances()
  request = gce_instances_client.delete(
      project=project.project_id,
      zone=project.default_zone,
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
  gce_disks_client = gcp_client.GceApi().disks()
  for disk in list(disks.keys())[1:]:
    log.info('Deleting disk: {0:s}.'.format(disk))
    while True:
      try:
        request = gce_disks_client.delete(
            project=project.project_id,
            zone=project.default_zone,
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
