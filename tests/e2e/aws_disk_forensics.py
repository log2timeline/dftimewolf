# -*- coding: utf-8 -*-
# Copyright 2022 Google Inc.
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
"""End to end test for the AWS -> GCP disk copy process."""
import json
import logging
import os
import unittest
import warnings

from libcloudforensics.providers.gcp.internal import compute, common, storage
from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.utils import storage_utils

import boto3

from dftimewolf import config
from dftimewolf.lib import resources, state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.recipes import manager as recipes_manager


log = logging.getLogger(__name__)

# pylint: disable=line-too-long
RECIPE = {
  'name': 'e2e-test-aws-to-gcp',
  'short_description': 'Nothing to see here.',
  'preflights': [
    {
      'wants': [],
      'name': 'AWSAccountCheck',
      'args': {
        'profile_name': '@aws_profile'
      }
    },{
      'wants': [],
      'name': 'GCPTokenCheck',
      'args': {
        'project_name': '@gcp_project'
      }
    }
  ],
  'modules': [
    {
      'wants': [],
      'name': 'AWSVolumeSnapshotCollector',
      'args': {
        'volumes': '@volumes',
        'region': '@aws_region'
      }
    },{
      'wants': ['AWSVolumeSnapshotCollector'],
      'name': 'AWSSnapshotS3CopyCollector',
      'args': {
        'snapshots': '',
        'bucket': '@aws_bucket',
        'region': '@aws_region',
        'subnet': '@subnet'
      }
    },{
      'wants': ['AWSSnapshotS3CopyCollector'],
      'name': 'S3ToGCSCopy',
      'args': {
        's3_objects': '',
        'aws_region': '@aws_region',
        'dest_project': '@gcp_project',
        'dest_bucket': '@gcp_bucket',
        'object_filter': '.+/image.bin$'
      }
    }, {
      'wants': ['S3ToGCSCopy'],
      'name': 'GCSToGCEImage',
      'args': {
        'source_objects': '',
        'dest_project': '@gcp_project'
      }
    }, {
      'wants': ['GCSToGCEImage'],
      'name': 'GCEDiskFromImage',
      'args': {
        'source_images': '',
        'dest_project': '@gcp_project',
        'dest_zone': '@gcp_zone'
      }
    }
  ],
  'args': [
    ['aws_region', 'AWS region containing the EBS volumes.', None],
    ['gcp_zone', 'Destination GCP zone in which to create the disks.', None],
    ['volumes', 'Comma separated list of EBS volume IDs (e.g. vol-xxxxxxxx).', None],
    ['aws_bucket', 'AWS bucket for image storage.', None],
    ['gcp_bucket', 'GCP bucket for image storage.', None],
    ['--subnet', 'AWS subnet to copy instances from, required if there is no default subnet in the volume region.', None],
    ['--gcp_project', 'Destination GCP project.', None],
    ['--aws_profile', 'Source AWS profile.', None],
  ]
}

TEST_MODULES = {
  'AWSAccountCheck': 'dftimewolf.lib.preflights.cloud_token',
  'AWSSnapshotS3CopyCollector': 'dftimewolf.lib.collectors.aws_snapshot_s3_copy',
  'AWSVolumeSnapshotCollector': 'dftimewolf.lib.collectors.aws_volume_snapshot',
  'GCEDiskFromImage': 'dftimewolf.lib.exporters.gce_disk_from_image',
  'GCPTokenCheck': 'dftimewolf.lib.preflights.cloud_token',
  'GCSToGCEImage': 'dftimewolf.lib.exporters.gcs_to_gce_image',
  'S3ToGCSCopy': 'dftimewolf.lib.exporters.s3_to_gcs'
}

INFO_REQUIRED_KEYS = ["gcp_project_id", "gcp_bucket", "gcp_zone", "aws_volume", "aws_region", "aws_bucket"]
# pylint: enable=line-too-long


class AWSToGCPForensicsEndToEndTest(unittest.TestCase):
  """End to end test of the AWS -> GCP disk copy workflow.

  This end-to-end test runs directly on AWS+GCP and tests the following modules:
    1. AWSVolumeSnapshotCollector
    2. AWSSnapshotS3CopyCollector
    3. S3ToGCSCopy
    4. GCSToGCEImage
    5. GCEDiskFromImage

  To run this test, add your project information to a project_info.json file:

  {
    "gcp_project_id": "xxx", # required
    "gcp_bucket": "xxx", # required
    "gcp_zone": "xxx", # required
    "aws_volume": "vol-xxx", # required
    "aws_region": "xxx", # required
    "aws_bucket": "xxx", # required
    "aws_subnet": "subnet-xxx" # Required if @aws_region has no default subnet
  }

  Export a PROJECT_INFO environment variable with the absolute path to your
  file: "user@terminal:~$ export PROJECT_INFO='absolute/path/project_info.json'"

  You also need to already be authenticated to AWS in some way. ENVVARS are
  recommended but otherwise see:
  https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html
  """

  def __init__(self, *args, **kwargs):
    super(AWSToGCPForensicsEndToEndTest, self).__init__(*args, **kwargs)
    try:
      project_info = ReadProjectInfo()
    except (OSError, RuntimeError, ValueError) as exception:
      self.error_msg = str(exception)
      return

    self.gcp_project_id = project_info['gcp_project_id']
    self.gcp_bucket = project_info['gcp_bucket']
    self.gcp_zone = project_info['gcp_zone']
    self.aws_volume = project_info['aws_volume']
    self.aws_region = project_info['aws_region']
    self.aws_bucket = project_info['aws_bucket']
    self.aws_subnet = project_info.get('aws_subnet', '')

  def setUp(self):
    self.incident_id = 'fake-incident-id'

    self.test_state = state.DFTimewolfState(config.Config)
    self._recipe = resources.Recipe("E2E Test Recipe", RECIPE, [])
    self._recipes_manager = recipes_manager.RecipesManager()
    self._recipes_manager.RegisterRecipe(self._recipe)

  def testRunRecipe(self):
    """Tests the recipe for AWS->GCP disk copy."""
    warnings.filterwarnings(
        action="ignore", message="unclosed", category=ResourceWarning)

    # Load the recipe, set the arguments, and run
    self.test_state.LoadRecipe(RECIPE, TEST_MODULES)
    self.test_state.command_line_options = {
      'aws_region': self.aws_region,
      'gcp_zone': self.gcp_zone,
      'volumes': self.aws_volume,
      'aws_bucket': self.aws_bucket,
      'gcp_bucket': self.gcp_bucket,
      'subnet': self.aws_subnet,
      'gcp_project': self.gcp_project_id
    }
    self.test_state.SetupModules()
    self.test_state.RunModules()

    # AWS Volume in count should equal GCE Disk out count, and be at least 1
    self.assertGreaterEqual(
        len(self.test_state.GetContainers(containers.AWSVolume)), 1)
    self.assertEqual(len(self.test_state.GetContainers(containers.AWSVolume)),
        len(self.test_state.GetContainers(containers.GCEDisk)))

    real_gce_disk_names = list(
        compute.GoogleCloudCompute(self.gcp_project_id).Disks().keys())

    for d in self.test_state.GetContainers(containers.GCEDisk):
      self.assertIn(d.name, real_gce_disk_names)
      real_disk = compute.GoogleComputeDisk(
          self.gcp_project_id, self.gcp_zone, d.name)
      self.assertEqual(real_disk.GetDiskType(), 'pd-standard')
      # Make an API call to the service that will fail if the disk doesn't exist

  def tearDown(self):
    """Clean up after the test."""
    log.warning("Cleaning up after test...")
    # All of the following artefacts are created: AWSSnapshot, AWSS3Object,
    # GCSObject, GCEImage, GCEDisk
    for c in self.test_state.GetContainers(containers.AWSSnapshot):
      self._removeAWSSnapshot(c.id)
    for c in self.test_state.GetContainers(containers.AWSS3Object):
      self._removeAWSS3Object(c.path)
    for c in self.test_state.GetContainers(containers.GCSObject):
      self._removeGCSObject(c.path)
    for c in self.test_state.GetContainers(containers.GCEImage):
      self._removeGCEImage(c.name)
    for c in self.test_state.GetContainers(containers.GCEDisk):
      self._removeGCEDisk(c.name)

  def _removeAWSSnapshot(self, snap_id: str):
    """Deletes an AWS EBS Snapshot with ID `id`."""
    log.warning(f'Deleting AWS EBS Snapshot {snap_id}')
    ec2_client = boto3.client('ec2', region_name=self.aws_region)
    try:
      ec2_client.delete_snapshot(SnapshotId=snap_id)
    except Exception as error:  # pylint: disable=broad-except
      log.error(f'Failed to delete AWS EBS Snapshot {snap_id}: {str(error)}')

  def _removeAWSS3Object(self, path: str):
    """Deletes an S3 object at `path`."""
    log.warning(f'Deleting AWS S3 object {path}')
    bucket, key = storage_utils.SplitStoragePath(path)
    s3_client = boto3.client('s3')
    try:
      s3_client.delete_object(Bucket=bucket, Key=key)
    except Exception as error:  # pylint: disable=broad-except
      log.error(f'Failed to delete S3 Object {path}: {str(error)}')

  def _removeGCSObject(self, path: str):
    """Delete a GCS object at `path`."""
    log.warning(f'Deleting GCS object {path}')
    try:
      storage.GoogleCloudStorage(self.gcp_project_id).DeleteObject(path)
    except Exception as error:  # pylint: disable=broad-except
      log.error(f'Failed to delete GCS Object {path}: {str(error)}')

  def _removeGCEImage(self, name: str):
    """Remove GCE Image with name `name`."""
    log.warning(f'Deleting GCE Image {name}')
    try:
      compute.GoogleComputeImage(
          self.gcp_project_id, self.gcp_zone, name
      ).Delete()
    except Exception as error:  # pylint: disable=broad-except
      log.error(f'Failed to delete GCE Image {name}: {str(error)}')

  def _removeGCEDisk(self, name: str):
    """Remove the disk with name `name`."""
    log.warning(f'Deleting GCE Disk {name}')
    try:
      gce_disk_client = common.GoogleCloudComputeClient(
          project_id=self.gcp_project_id).GceApi().disks()
      gce_disk_client.delete(
          project=self.gcp_project_id,
          zone=self.gcp_zone,
          disk=name
      ).execute()
    except Exception as error:  # pylint: disable=broad-except
      log.error(f'Failed to delete GCE Disk {name}: {str(error)}')


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
      raise RuntimeError(
          f'Error: cannot parse JSON file. {str(exception)}') from ValueError
    json_file.close()
  except OSError as exception:
    raise OSError(
        f'Error: could not open/close file {project_info}: {str(exception)}'
        ) from OSError

  if not all(key in project_info for key in INFO_REQUIRED_KEYS):
    raise ValueError(
        'Error: please make sure that your JSON file has the required entries. '
        'The file should contain at least the following: '
        f'{", ".join(INFO_REQUIRED_KEYS)}')

  return project_info


if __name__ == '__main__':
  unittest.main()
