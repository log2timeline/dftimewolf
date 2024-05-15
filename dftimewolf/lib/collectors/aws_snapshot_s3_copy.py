# Lint as: python3
"""Copies AWS EBS snapshots into AWS S3."""

import time
from typing import Any, Optional, Type, List
import boto3

from libcloudforensics.providers.aws import forensics
from libcloudforensics.providers.aws.internal import account
from libcloudforensics.errors import ResourceCreationError
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


INSTANCE_PROFILE_NAME = 'ebsCopy'


class AWSSnapshotS3CopyException(Exception):
  """Class to represent an exception in this collector.
  Attributes:
    message (str): The error message.
  """

  def __init__(self,
               message: str) -> None:
    """Initializes the Exception with provided message.
    Args:
      message (str): The error message.
    """
    super().__init__(message)
    self.message = message


class AWSSnapshotS3CopyCollector(module.ThreadAwareModule):
  """Copies AWS EBS snapshots into AWS S3.

  Snapshot list can be passed in via SetUp parameters, or from an
  AWSAttributeContainer from a previous module.

  Attributes:
    snapshots: The snapshots to copy.
    bucket: The destination S3 bucket.
  """

  def __init__(self,
      state: DFTimewolfState,
      name: Optional[str]=None,
      critical: Optional[bool]=False) -> None:
    """Initializes a AWSVolumeToS3 collector."""
    super(AWSSnapshotS3CopyCollector, self).__init__(
        state, name=name, critical=critical)
    self.bucket: str = ''
    self.region: str = ''
    self.subnet: Any = None
    self.ec2: Any = None
    self.s3: Any = None
    self.iam_details: Any = None
    self.aws_account = None
    self.bucket_exists: bool = False

  # pylint: disable=arguments-differ
  def SetUp(self,
            snapshots: Optional[str] = '',
            bucket: str='',
            region: str='',
            subnet: Optional[str]=None) -> None:
    """Sets up the AWSVolumeToS3 collector.

    Args:
      snapshots (str): Comma seperated list of snapshot IDs.
      bucket (str): The destination s3 bucket.
      region (str): The AWS region the snapshots are in.
      subnet (str): The subnet to use for the copy instance. Required if there
        is no default subnet.
    """
    self.bucket = bucket
    self.region = region
    self.subnet = subnet
    self.ec2 = boto3.client('ec2', region_name=self.region)
    self.s3 = boto3.client('s3', region_name=self.region)
    self.aws_account = account.AWSAccount(
          self._PickAvailabilityZone(self.subnet))

    if snapshots:
      for snap in snapshots.split(','):
        self.StoreContainer(containers.AWSSnapshot(snap))

    # Check the bucket exists
    self.bucket_exists = self._CheckBucketExists(self.bucket)

  def PreProcess(self) -> None:
    """Set up for the snapshot copy operation."""
    if not self.bucket_exists:
      self.logger.info(f'Creating AWS bucket {self.bucket:s}')

      create_bucket_args = {'Bucket': self.bucket}
      # us-east-1 is the default, but throws an error if actually specified.
      if self.region != 'us-east-1':
        create_bucket_args['LocationConstraint'] = self.region
      self.s3.create_bucket(**create_bucket_args)

    # Check the snapshots exist
    snap_ids = [snap.id for snap in \
        self.GetContainers(containers.AWSSnapshot)]
    if not self._CheckSnapshotsExist(snap_ids):
      self.ModuleError(
          'Could not find the snapshots ids to copy.',
          critical=True)

    # Create the IAM pieces
    self.iam_details = forensics.CopyEBSSnapshotToS3SetUp(
        self.aws_account, INSTANCE_PROFILE_NAME)
    if self.iam_details['profile']['created']:
      time.sleep(20) # Propagation delay

  def Process(self, container: containers.AWSSnapshot
              ) -> None:  # pytype: disable=signature-mismatch
    """Perform the copy of the snapshot to S3."""

    # Aws accounts have thread safety issues. Create a unique one per thread
    aws_account = account.AWSAccount(self._PickAvailabilityZone(self.subnet))
    try:
      result = forensics.CopyEBSSnapshotToS3Process(aws_account,
          self.bucket,
          container.id,
          self.iam_details['profile']['arn'],
          subnet_id=self.subnet)

      self.StoreContainer(containers.AWSS3Object(result['image']))
      for h in result['hashes']:
        self.StoreContainer(containers.AWSS3Object(h))
    except ResourceCreationError as exception:
      self.ModuleError(
          f'Exception during copy operation: {exception!s}', critical=True)

  def PostProcess(self) -> None:
    """Clean up afterwards."""
    forensics.CopyEBSSnapshotToS3TearDown(
        self.aws_account, INSTANCE_PROFILE_NAME, self.iam_details)

  # pylint: disable=inconsistent-return-statements
  def _PickAvailabilityZone(self, subnet: Optional[str]='') -> str:
    """Given a region + subnet, pick an availability zone.

    If the subnet is provided, it's AZ is returned. Otherwise, one is picked
    from those available in the region.

    Args:
      subnet (str): Optional. An EC2 subnet ID.

    Returns:
      A string representing the AZ.

    Raises:
      AWSSnapshotS3CopyException: If no suitable AZ can be found.
    """
    # If we received a subnet ID, return the AZ for it
    if subnet:
      subnets = self.ec2.describe_subnets(SubnetIds=[subnet])
      return str(subnets['Subnets'][0]['AvailabilityZone'])

    # Otherwise, pick one.
    response = self.ec2.describe_availability_zones(
      Filters=[{'Name': 'region-name','Values': [self.region]}])
    for zone in response['AvailabilityZones']:
      if zone['State'] == 'available':
        return str(zone['ZoneName'])

    # If we reached here, we have a problem
    raise AWSSnapshotS3CopyException('No suitable availability zone found')

  def _CheckSnapshotsExist(self, snap_ids: List[str]) -> bool:
    """Check the snapshots that we want to copy exist.

    Args:
      snap_ids (List[str]): A list of snapshot IDs to look for.
    Returns:
      True if the snapshots all exist and we have permissions to list them,
          False otherwise.
    """
    try:
      self.ec2.describe_snapshots(SnapshotIds=snap_ids)
    except self.ec2.exceptions.ClientError:
      return False
    return True

  def _CheckBucketExists(self, bucket_name: str) -> bool:
    """Checks whether a bucket exists in the configured AWS account.

    Args:
      bucket_name (str): The bucket name to look for.
    Returns:
      True if the bucket exists and we have permissions to confirm that, False
          otherwise.
    """
    buckets = [bucket['Name'] for bucket in self.s3.list_buckets()['Buckets']]
    return bucket_name in buckets

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    return containers.AWSSnapshot

  def GetThreadPoolSize(self) -> int:
    return 10


modules_manager.ModulesManager.RegisterModule(AWSSnapshotS3CopyCollector)
