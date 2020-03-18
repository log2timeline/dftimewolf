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

log = logging.getLogger()


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

  def setUp(self):
    super(EndToEndTest, self).setUp()
    self.analysis_vm = None
    self.incident_id = 'fake-incident-id'
    self.test_state = None

    project_info = os.environ.get('PROJECT_INFO')

    if project_info is None:
      raise unittest.SkipTest('Error: please make sure that you defined the '
                              '"PROJECT_INFO" environment variable pointing '
                              'to your project settings.')
    try:
      json_file = open(project_info)
      project_info = json.load(json_file)
      json_file.close()
    except ValueError as exception:
      raise unittest.SkipTest('Error: cannot parse JSON file. {0:s}'.format(
          str(exception)))

    if not all(key in project_info for key in ['project_id', 'instance',
                                               'zone']):
      raise unittest.SkipTest('Error: please make sure that your JSON file '
                              'has the required entries. The file should '
                              'contain at least the following: ["project_id", '
                              '"instance", "zone"].')

    self.project_id = project_info['project_id']
    self.instance_to_analyse = project_info['instance']
    # Optional: test a disk other than the boot disk
    if 'disk' in project_info:
      self.disk_to_forensic = project_info['disk']
    else:
      self.disk_to_forensic = None
    self.zone = project_info['zone']

  def test_end_to_end(self):
    """End to end test on GCP for the gcloud.py collector.

    This end-to-end test runs directly on GCP and tests that:
      1. The gcloud.py collector connects to the target instance and makes a
      snapshot of the boot disk (by default) or of the disk passed in
      parameter to the collector's SetUp method (disk_names).
      2. A new disk is created from the taken snapshot.
      3. If an analysis VM already exists, the module will attach the disk
      copy to the VM. Otherwise, it will create a new GCP instance for
      analysis purpose and attach the disk copy to it.
    """

    self.test_state = state.DFTimewolfState(config.Config)
    gcloud_collector = gcloud.GoogleCloudCollector(self.test_state)
    self.assertIsNotNone(gcloud_collector)

    # This should make a copy of the boot disk only
    gcloud_collector.SetUp(
        self.project_id,
        self.project_id,
        self.incident_id,
        self.zone,
        42.0,
        16,
        remote_instance_name=self.instance_to_analyse,
    )

    self.analysis_vm = gcloud_collector.analysis_vm

    # Check that the collector is correctly initialized
    self.assertEqual(self.test_state.errors, [])
    self.assertEqual(gcloud_collector.disk_names, [])
    self.assertEqual(gcloud_collector.analysis_project.project_id,
                     self.project_id)
    self.assertEqual(gcloud_collector.remote_project.project_id,
                     self.project_id)
    self.assertEqual(gcloud_collector.remote_instance_name,
                     self.instance_to_analyse)
    self.assertEqual(gcloud_collector.all_disks, False)

    # Attach the disk copy to the analysis VM
    gcloud_collector.Process()

    self.assertEqual(
        self.test_state.output[0][0], 'gcp-forensics-vm-fake-incident-id')
    self.assertIsInstance(self.test_state.output[0][1], gcp.GoogleComputeDisk)
    self.assertTrue(self.test_state.output[0][1].name.startswith(
        'incidentfake-incident-id'))
    self.assertTrue(self.test_state.output[0][1].name.endswith('-copy'))
    self.assertIsInstance(self.analysis_vm, gcp.GoogleComputeInstance)
    self.assertEqual(self.analysis_vm.name, 'gcp-forensics-vm-fake-incident-id')

    disks = self.analysis_vm.list_disks()
    self.assertEqual(
        disks,
        ['gcp-forensics-vm-fake-incident-id',
         self.test_state.output[0][1].name])

    if self.disk_to_forensic is None:
      self.__clean()
      return

    # This should make a copy of the disk specified in 'disk-names'
    gcloud_collector.SetUp(
        self.project_id,
        self.project_id,
        self.incident_id,
        self.zone,
        42.0,
        16,
        remote_instance_name=self.instance_to_analyse,
        disk_names=self.disk_to_forensic
    )

    self.analysis_vm = gcloud_collector.analysis_vm

    # Attach the disk copy to the analysis VM
    gcloud_collector.Process()

    self.assertEqual(
        self.test_state.output[1][0], 'gcp-forensics-vm-fake-incident-id')
    self.assertIsInstance(self.test_state.output[1][1], gcp.GoogleComputeDisk)
    self.assertTrue(self.test_state.output[1][1].name.startswith(
        'incidentfake-incident-id'))
    self.assertTrue(self.test_state.output[1][1].name.endswith('-copy'))

    disks = self.analysis_vm.list_disks()
    self.assertEqual(disks,
                     ['gcp-forensics-vm-fake-incident-id',
                      self.test_state.output[0][1].name,
                      self.test_state.output[1][1].name])

    self.__clean()

  def __clean(self):
    project = gcp.GoogleCloudProject(project_id=self.project_id,
                                     default_zone=self.zone)

    disks = self.analysis_vm.list_disks()

    # delete the created forensics VMs
    log.info('Deleting analysis instance: {0:s}.'.format(
        self.analysis_vm.name))
    operation = project.gce_api().instances().delete(
        project=project.project_id,
        zone=self.zone,
        instance=self.analysis_vm.name
    ).execute()
    try:
      project.gce_operation(operation, block=True)
    except HttpError:
      # gce_operation triggers a while(True) loop that checks on the
      # operation ID. Sometimes it loops one more time right when the
      # operation has finished and thus the associated ID doesn't exists
      # anymore, throwing an HttpError. We can ignore this.
      pass
    log.info('Instance {0:s} successfully deleted.'.format(
        self.analysis_vm.name))

    # delete the copied disks
    # we ignore the disk that was created for the analysis VM (disks[0]) as
    # it is deleted in the previous operation
    for disk in disks[1:]:
      log.info('Deleting disk: {0:s}.'.format(disk))
      while True:
        try:
          operation = project.gce_api().disks().delete(
              project=project.project_id,
              zone=self.zone,
              disk=disk
          ).execute()
          project.gce_operation(operation, block=True)
          break
        except HttpError as exception:
          # The gce api will throw a 400 until the analysis vm's deletion is
          # correctly propagated. When the disk is finally deleted, it will
          # throw a 404 not found if it looped one more time after deletion.
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
