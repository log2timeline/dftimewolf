# Lint as: python3
"""Copies AWS EBS snapshots into AWS S3."""

import threading
import time
from typing import Any, Optional, Type
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
    self.iam_details: Any = None
    self.aws_account = None

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

    if snapshots:
      for snap in snapshots.split(','):
        self.state.StoreContainer(containers.AWSSnapshot(snap))

  def PreProcess(self) -> None:
    """Set up for the snapshot copy operation."""
    # Validate the bucket exists. If not, create it.
    try:
      self.aws_account = account.AWSAccount(
          self._PickAvailabilityZone(self.subnet))
      s3 = boto3.client('s3', region_name=self.region)
    except AWSSnapshotS3CopyException as exception:
      self.ModuleError(
          'Error encountered determining availability zone: {0!s}'.format(
              exception), critical=True)

    if self.bucket not in [bucket['Name']
        for bucket in s3.list_buckets()['Buckets']]:
      self.logger.info('Creating AWS bucket {0:s}'.format(self.bucket))
      s3.create_bucket(
        Bucket=self.bucket,
        CreateBucketConfiguration={'LocationConstraint': self.region})

    # Check the snapshots exist
    try:
      cont_list = self.state.GetContainers(containers.AWSSnapshot)
      snaps = [snap.snap_id for snap in cont_list]
      self.ec2.describe_snapshots(SnapshotIds=snaps)
    except self.ec2.exceptions.ClientError as exception:
      self.ModuleError('Error encountered describing snapshots: {0!s}'.
          format(exception), critical=True)

    # Create the IAM pieces
    self.iam_details = forensics.CopyEBSSnapshotToS3SetUp(
        self.aws_account, INSTANCE_PROFILE_NAME)
    if self.iam_details['profile']['created']:
      time.sleep(20) # Propagation delay

  def Process(self, container: containers.AWSSnapshot) -> None:
    """Perform the copy of the snapshot to S3."""

    # Aws accounts have thread safety issues. Create a unique one per thread
    aws_account = account.AWSAccount(self._PickAvailabilityZone(self.subnet))
    try:
      result = forensics.CopyEBSSnapshotToS3Process(aws_account,
          self.bucket,
          container.snap_id,
          self.iam_details['profile']['arn'],
          subnet_id=self.subnet)

      self.state.StoreContainer(containers.AWSS3Object(result['image']))
      for h in result['hashes']:
        self.state.StoreContainer(containers.AWSS3Object(h))
    except ResourceCreationError as exception:
      self.ModuleError('Exception during copy operation: {0!s}'.
          format(exception), critical=True)

  def PostProcess(self) -> None:
    """Clean up afterwards."""
    forensics.CopyEBSSnapshotToS3TearDown(
        self.aws_account, INSTANCE_PROFILE_NAME, self.iam_details)

  # pylint: disable=inconsistent-return-statements
  def _PickAvailabilityZone(self, subnet: str='') -> str:
    """Given a region + subnet, pick an availability zone.

    If the subnet is provided, it's AZ is returned. Otherwise, one is picked
    from those available in the region.

    Args:
      subnet (str): Optional. An EC2 subnet ID.

    Returns:
      A string representing the AZ.

    Raises:
      AWSSnapshotS3CopyException: If no suitable AZ can be found."""
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

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.AWSSnapshot

  def GetThreadPoolSize(self) -> int:
    return 10

  def PreSetUp(self) -> None:
    pass

  def PostSetUp(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(AWSSnapshotS3CopyCollector)
