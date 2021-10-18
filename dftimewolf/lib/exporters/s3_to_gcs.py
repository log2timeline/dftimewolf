# -*- coding: utf-8 -*-
"""Export objects from AWS S3 to a GCP GCS bucket."""

import re
from typing import Any, Optional, Type

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.utils.storage_utils import SplitStoragePath
from google.cloud.storage.client import Client as storage_client
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


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
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes a copy of objects from AWS S3 to a GCS bucket.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(S3ToGCSCopy, self).__init__(
        state, name=name, critical=critical)
    self.aws_region: str = ''
    self.dest_project_name: str = ''
    self.dest_project: gcp_project.GoogleCloudProject = ''
    self.dest_bucket: str = ''
    self.filter: Any = None

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
    self.filter = object_filter

    if s3_objects:
      for obj in s3_objects.split(','):
        self.state.StoreContainer(containers.AWSS3Object(obj))

  def PreProcess(self) -> None:
    """Prep work for copying objects from S3 to GCS - Bucket creation."""
    # Check if the destination bucket exists. If not, create it.
    if not self.dest_bucket:
      self.ModuleError('No destination GCP bucket specified', critical=True)
    buckets = [b['id'] for b in self.dest_project.storage.ListBuckets()]
    if self.dest_bucket not in buckets:
      self.logger.info('Creating GCS bucket {0:s}'.format(self.dest_bucket))
      self.dest_project.storage.CreateBucket(self.dest_bucket)

    # Set the permissions on the bucket
    self.logger.info('Applying permissions to bucket')
    self._SetBucketServiceAccountPermissions()

  def Process(self, container: containers.AWSS3Object) -> None:
    """Creates and exports disk image to the output bucket."""
    if self.filter:
      if not re.match(self.filter, container.path):
        self.logger.info('{0:s} does not match filter. Skipping.'\
            .format(container.path))
        return

    # We must create a new client for each thread, rather than use the class
    # member self.dest_project due to an underlying thread safety issue in
    # httplib2: https://github.com/googleapis/google-cloud-python/issues/3501
    client = gcp_project.GoogleCloudProject(self.dest_project_name)
    client.storagetransfer.S3ToGCS(
        container.path, self.aws_region + 'a', 'gs://' + self.dest_bucket)
    _, s3_path = SplitStoragePath(container.path)
    output = self.dest_bucket + '/' + s3_path
    self.state.StoreContainer(containers.GCSObject(output))

  def _SetBucketServiceAccountPermissions(self) -> None:
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

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.AWSS3Object

  def GetThreadPoolSize(self) -> int:
    # https://cloud.google.com/storage-transfer/quotas
    # limit is 100 per 100 seconds, or 1000/day.
    return 30

  def PreSetUp(self) -> None:
    pass

  def PostSetUp(self) -> None:
    pass

  def PostProcess(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(S3ToGCSCopy)
