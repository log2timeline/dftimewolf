# -*- coding: utf-8 -*-
"""Export objects from AWS S3 to a GCP GCS bucket."""

from time import sleep

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeDisk

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, aws_containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState
from libcloudforensics.errors import ResourceCreationError
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.providers.utils.storage_utils import SplitStoragePath

from google.cloud.storage.client import Client as storage_client

import threading

class S3ToGCSCopy(module.BaseModule):
  """AWS S3 objects to GCP GCS.

  Attributes:
    aws_region (srt): AWS region (for account.AWSAccount creation).
    dest_project (gcp_project.GoogleCloudProject): Destination project with the
      destination GCS bucket.
    dest_project_name (str): Name of the destination project. used to create
      the dest_project.
    dest_bucket (str): Destination bucket in the GCP project.
    s3_objects (List[str]): Objects to be copied.
  """

  def __init__(self, state, name=None, critical=False):
    """Initializes a copy of objects from AWS S3 to a GCS bucket.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(S3ToGCSCopy, self).__init__(
        state, name=name, critical=critical)
    self.aws_region = None
    self.dest_project_name = None
    self.dest_project = None
    self.dest_bucket = None
    self.s3_objects = None
    self._lock = threading.Lock()
    self.thread_error = None

  # pylint: disable=arguments-differ
  def SetUp(self,
            aws_region,
            dest_project,
            dest_bucket,
            s3_objects=None):
    """Sets up a copy operation from AWS S3 to GCP GCS.

    AWS objects to copy are sourced from either the state, or passed in here.
    Args:
      aws_region (str): The AWS region (for account.AWSAccount creation).
      dest_project (str): The destination GCP project.
      dest_bucket (str): The destination GCP bucket.
      s3_objects (str): Comma separated list of objects to copy from S3. Each
        should be of the form 's3://bucket-name/path/to/object'
    """
    self.aws_region = aws_region
    self.dest_project_name = dest_project
    self.dest_bucket = dest_bucket
    self.dest_project = gcp_project.GoogleCloudProject(self.dest_project_name)
    self.s3_objects = s3_objects

  def Process(self) -> None:
    """Creates and exports disk image to the output bucket."""
    # The list of s3 objects could have been set in SetUp, or it might come
    # from a container from a previous module. Check where they come from, and
    # validate them.
    if self.s3_objects:
      self.s3_objects = self.s3_objects.split(',')
    # Right now, there is only one module that generates S3 paths for copy.
    elif len(self.state.GetContainers(aws_containers.AWSAttributeContainer)):
      self.s3_objects = [image.image_path
          for image in self.state.GetContainers(
            aws_containers.AWSAttributeContainer)[0].s3_images]
    else:
      self.ModuleError('No s3 objects to copy specified', critical=True)

    # Check if the destination bucket exists. If not, create it.
    if not self.dest_bucket:
      self.ModuleError('No destination GCP bucket specified', critical=True)
    if self.dest_bucket not in \
        [bucket['id'] for bucket in self.dest_project.storage.ListBuckets()]:
      self.logger.info('Creating GCS bucket {0:s}'.format(self.dest_bucket))
      self.dest_project.storage.CreateBucket(self.dest_bucket)

    # Set the permissions on the bucket
    self.logger.info('Applying permissions to bucket')
    self._SetBucketServiceAccountPermissions()

    threads = []
    self.logger.info(
      'Starting {0:d} transfer threads, expect log messages from each'\
        .format(len(self.s3_objects)))
    for s3_object in self.s3_objects:
      try:
        thread = threading.Thread(
          target=self._PerformCopyThread, args=((s3_object,)))
        thread.start()
        threads.append(thread)
        sleep(2) # Offest each thread start slightly
      except ResourceCreationError as exception:
        self.ModuleError('Exception during transfer operation: {0!s}'\
          .format(exception), critical=True)

    for thread in threads:
      thread.join()

    if self.thread_error:
      self.ModuleError('Exception during transfer operation: {0!s}'\
        .format(self.thread_error), critical=True)

  def _PerformCopyThread(self, s3_object) -> None:
    try:
      # We must create a new client for each thread, rather than use the class
      # member self.dest_project due to an underlying thread safety issue in
      # httplib2: https://github.com/googleapis/google-cloud-python/issues/3501
      client = gcp_project.GoogleCloudProject(self.dest_project_name)
      client.storagetransfer.S3ToGCS(s3_object, self.aws_region + 'a', 'gs://' + self.dest_bucket)
      _, s3_path = SplitStoragePath(s3_object)
      output = self.dest_bucket + '/' + s3_path

      with self._lock:
        if len(self.state.GetContainers(containers.GCSObjectList)):
          self.state.GetContainers(containers.GCSObjectList)[0]\
              .append(output)
        else:
          container = containers.GCSObjectList()
          container.append(output)
          self.state.StoreContainer(container)

    except Exception as e: # pylint: disable=broad-except
      self.logger.critical('{0!s}'.format(e))
      self.thread_error = e

  def _SetBucketServiceAccountPermissions(self):
    """Grant access to the storage transfer service account to use the bucket.
    See https://cloud.google.com/storage-transfer/docs/configure-access#sink"""

    request = self.dest_project.storagetransfer.GcstApi().\
        googleServiceAccounts().get(projectId=self.dest_project_name)
    service_account = request.execute()['accountEmail']

    client = storage_client(project=self.dest_project_name)
    bucket = client.get_bucket(self.dest_bucket)
    policy = bucket.get_iam_policy(requested_policy_version=3)
    policy.version = 3

    policy.bindings.append({
        'role': 'roles/storage.legacyBucketWriter',
        'members': ['serviceAccount:' + service_account],
    })
    policy.bindings.append({
        'role': 'roles/storage.objectViewer',
        'members': ['serviceAccount:' + service_account],
    })

    bucket.set_iam_policy(policy)


modules_manager.ModulesManager.RegisterModule(S3ToGCSCopy)
