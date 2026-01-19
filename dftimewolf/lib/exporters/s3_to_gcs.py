# -*- coding: utf-8 -*-
"""Export objects from AWS S3 to a GCP GCS bucket."""

import re
from typing import Any, Callable, Type

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.utils.storage_utils import SplitStoragePath
from libcloudforensics.errors import ResourceCreationError
from google.cloud.storage.client import Client as storage_client
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import cache
from dftimewolf.lib import telemetry
from dftimewolf.lib.containers import manager as container_manager


class S3ToGCSCopy(module.ThreadAwareModule):
  """AWS S3 objects to GCP GCS.

  Attributes:
    aws_region (str): AWS region (for account.AWSAccount creation).
    dest_project (gcp_project.GoogleCloudProject): Destination project with the
      destination GCS bucket.
    dest_project_name (str): Name of the destination project. used to create
      the dest_project.
    dest_bucket (str): Destination bucket in the GCP project.
    s3_objects (List[str]): Objects to be copied.
    filter (str): regex filter for objects to copy - Useful when the files are
      from a previous module.
  """

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initializes a copy of objects from AWS S3 to a GCS bucket.

    Args:
      name: The modules runtime name.
      container_manager_: A common container manager object.
      cache_: A common DFTWCache object.
      telemetry_: A common telemetry collector object.
      publish_message_callback: A callback to send modules messages to.
    """
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)

    self.aws_region: str = ''
    self.dest_project_name: str = ''
    self.dest_project: gcp_project.GoogleCloudProject = None
    self.dest_bucket: str = ''
    self.filter: Any = None
    self.bucket_exists = False

  # pylint: disable=arguments-differ
  def SetUp(self,
            aws_region: str,
            dest_project: str,
            dest_bucket: str,
            s3_objects: str='',
            object_filter: str='') -> None:
    """Sets up a copy operation from AWS S3 to GCP GCS.

    AWS objects to copy are sourced from either the state, or passed in here.
    Args:
      aws_region (str): The AWS region (for account.AWSAccount creation).
      dest_project (str): The destination GCP project.
      dest_bucket (str): The destination GCP bucket.
      s3_objects (str): Comma separated list of objects to copy from S3. Each
        should be of the form 's3://bucket-name/path/to/object'
      object_filter (str): regex filter for objects to copy - Useful when the
        files are from a previous module but not all should be transferred.
    """
    self.aws_region = aws_region
    self.dest_project_name = dest_project
    self.dest_bucket = dest_bucket
    self.dest_project = gcp_project.GoogleCloudProject(self.dest_project_name)
    self.bucket_exists = self._CheckBucketExists(self.dest_bucket)

    if not self.dest_bucket:
      self.ModuleError('No destination GCP bucket specified', critical=True)

    if object_filter:
      self.filter = re.compile(object_filter)

    if s3_objects:
      for obj in s3_objects.split(','):
        self.StoreContainer(containers.AWSS3Object(obj))

  def PreProcess(self) -> None:
    """Prep work for copying objects from S3 to GCS - Bucket creation."""
    # Check if the destination bucket exists. If not, create it.
    if not self.bucket_exists:
      try:
        self.dest_project.storage.CreateBucket(self.dest_bucket)
      except ResourceCreationError as exception:
        self.ModuleError(str(exception), critical=True)

    # Set the permissions on the bucket
    self.logger.info('Applying permissions to bucket')
    try:
      self._SetBucketServiceAccountPermissions()
    except Exception as exception: # pylint: disable=broad-except
      self.ModuleError(str(exception), critical=True)

  def Process(self, container: containers.AWSS3Object
              ) -> None:  # pytype: disable=signature-mismatch
    """Creates and exports disk image to the output bucket."""
    if self.filter and not self.filter.match(container.path):
      self.logger.debug(
        "{0:s} does not match filter. Skipping.".format(container.path)
      )
      return

    # Grab the first AWS Availability Zone in the region. AWS availability zones
    # are named for the region, appended with a, b, c...
    az = self.aws_region + 'a'

    # We must create a new client for each thread, rather than use the class
    # member self.dest_project due to an underlying thread safety issue in
    # httplib2: https://github.com/googleapis/google-cloud-python/issues/3501
    client = gcp_project.GoogleCloudProject(self.dest_project_name)
    client.storagetransfer.S3ToGCS(
        container.path, az, 'gs://' + self.dest_bucket)
    _, s3_path = SplitStoragePath(container.path)
    output = self.dest_bucket + '/' + s3_path
    self.StoreContainer(containers.GCSObject(output))

  def _SetBucketServiceAccountPermissions(self) -> None:
    """Grant access to the storage transfer service account to use the bucket.

    See https://cloud.google.com/storage-transfer/docs/configure-access#sink"""
    request = self.dest_project.storagetransfer.GcstApi().\
        googleServiceAccounts().get(projectId=self.dest_project_name)  # pylint: disable=no-member
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

  def _CheckBucketExists(self, bucket_name: str) -> bool:
    """Check that the GCS bucket exists.

    Args:
      bucket_name (str): The GCS buncket name to check for.
    Returns:
      True if we have perms to list the bucket, and it exists, false otherwise.
    """
    buckets = [b['id'] for b in self.dest_project.storage.ListBuckets()]
    return bucket_name in buckets

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    return containers.AWSS3Object

  def GetThreadPoolSize(self) -> int:
    # https://cloud.google.com/storage-transfer/quotas
    # limit is 100 per 100 seconds, or 1000/day.
    return 30

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(S3ToGCSCopy)
