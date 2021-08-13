# Lint as: python3
"""Copies AWS EBS snapshots into AWS S3."""

import threading
from time import sleep
import boto3
from typing import Any, Optional

from libcloudforensics.providers.aws import forensics
from libcloudforensics.providers.aws.internal import account
from libcloudforensics.errors import ResourceCreationError
from dftimewolf.lib import module
from dftimewolf.lib.containers import aws_containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


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


class AWSSnapshotS3CopyCollector(module.BaseModule):
  """Copies AWS EBS snapshots into AWS S3. Snapshot list can be passed in via
  SetUp parameters, or from a AWSAttributeContainer from a previous module.

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
    self.snapshots: Any = None
    self.bucket: str = ''
    self.region: str = ''
    self.subnet: str = ''
#    self.ec2 = None
    self._lock = threading.Lock()
    self.thread_error: Any = None

  # pylint: disable=arguments-differ
  def SetUp(self,
            snapshots: str = '',
            bucket: str='',
            region: str='',
            subnet: str='') -> None:
    """Sets up the AWSVolumeToS3 collector.

    Args:
      snapshots (str): Comma seperated list of snapshot IDs. If not specified,
        will look for an AWS snapshot list container for state from a previous
        module.
      bucket (str): The destination s3 bucket.
      region (str): The AWS region the snapshots are in.
      subnet (str): The subnet to use for the copy instance. Required if there
        is no default subnet.
    """
    self.snapshots = snapshots
    self.bucket = bucket
    self.region = region
    self.subnet = subnet
    self.ec2 = boto3.client('ec2', region_name=self.region)

  def Process(self) -> None:
    """Images the volumes into S3."""
    # The list of snapshots could have been set in SetUp, or it might come
    # from a container from a previous module. Check where they come from, and
    # validate them.
    if self.snapshots:
      self.snapshots = self.snapshots.split(',')
    elif len(self.state.GetContainers(aws_containers.AWSAttributeContainer)):
      self.snapshots = self.state.GetContainers(
        aws_containers.AWSAttributeContainer)[0].snapshots
    else:
      self.ModuleError('No snapshot IDs specified', critical=True)

    # Validate the bucket exists. If not, create it.
    s3 = boto3.client('s3', region_name=self.region)

    if self.bucket not in \
        [bucket['Name'] for bucket in s3.list_buckets()['Buckets']]:
      self.logger.info('Creating AWS bucket {0:s}'.format(self.bucket))
      s3.create_bucket(
        Bucket=self.bucket,
        CreateBucketConfiguration={'LocationConstraint': self.region})

    # Check the snapshots exist
    try:
      self.ec2.describe_snapshots(SnapshotIds=self.snapshots)
      zone = self._PickAvailabilityZone(self.subnet)
    except self.ec2.exceptions.ClientError as exception:
      self.ModuleError('Error encountered describing snapshots: {0!s}'.\
        format(exception), critical=True)
    except AWSSnapshotS3CopyException as exception:
      self.ModuleError('Error encountered determining availability zone: {0!s}'.\
        format(exception), critical=True)

    # Perform the prep stage
    instance_profile_name = 'ebsCopy'
    aws_account = account.AWSAccount(zone)
    iam_details = forensics.CopyEBSSnapshotToS3SetUp(
        aws_account, instance_profile_name)
    if iam_details['profile']['created']: # Propagation delay
      sleep(20)

    # Kick off a thread for each snapshot to perform the copy.
    threads = []
    self.logger.info(
      'Starting {0:d} copy threads, expect log messages from each'\
        .format(len(self.snapshots)))
    for snapshot in self.snapshots:
      try:
        thread = threading.Thread(
            target=self._PerformCopyThread, args=(
                snapshot, aws_account, iam_details['profile']['arn']))
        thread.start()
        threads.append(thread)
        sleep(2) # Offest each thread start slightly
      except ResourceCreationError as exception:
        self.ModuleError('Exception during copy operation: {0!s}'\
          .format(exception), critical=True)

    for thread in threads:
      thread.join()

    forensics.CopyEBSSnapshotToS3TearDown(
        aws_account, instance_profile_name, iam_details)

    if self.thread_error:
      self.ModuleError('Exception during copy operation: {0!s}'\
        .format(self.thread_error), critical=True)

    self.logger.info('Snapshot copy complete! results:')
    for image in self.state.GetContainers(
        aws_containers.AWSAttributeContainer)[0].s3_images:
      self.logger.info('Image: {0:s} - Hashes: {1:s}'.format(
        image.image_path,
        ','.join(image.hash_paths)
      ))

  def _PerformCopyThread(self,
      snapshot_id: str,
      aws_account: account.AWSAccount,
      instance_profile_arn: str) -> None:
    """Perform the copy operation. Designed to be called as a new thread from
    Process(). Will place the output file paths into the state container,
    (creating it if it doesn't exist already.)

    Args:
      snapshot_id (str): The snapshot ID.
      aws_account (account.AWSAccount): The AWS account object.
      """
    try:
      result = forensics.CopyEBSSnapshotToS3Process(aws_account,
          self.bucket,
          snapshot_id,
          instance_profile_arn,
          subnet_id=self.subnet)
      output = aws_containers.S3Image(result['image'], result['hashes'])

      with self._lock:
        if len(self.state.GetContainers(aws_containers.AWSAttributeContainer)):
          self.state.GetContainers(aws_containers.AWSAttributeContainer)[0]\
              .AppendS3Image(output)
        else:
          container = aws_containers.AWSAttributeContainer()
          container.AppendS3Image(output)
          self.state.StoreContainer(container)
    except Exception as e: # pylint: disable=broad-except
      self.logger.critical('{0!s}'.format(e))
      self.thread_error = e

  # pylint: disable=inconsistent-return-statements
  def _PickAvailabilityZone(self, subnet: str='') -> str:
    """Given a region + subnet, pick an availability zone. If the subnet is
    provided, it's AZ is returned. Otherwise, one is picked from those
    available in the region.

    Args:
      ec2 (boto3.client): EC2 client.
      subnet (str): Optional. An EC2 subnet ID.

    Returns:
      A string representing the AZ.
    
    Raises:
      AWSSnapshotS3CopyException: If no suitable AZ cvan be found."""
    # If we received a subnet ID, return the AZ for it
    if subnet:
      return str(self.ec2.describe_subnets(SubnetIds=[subnet])\
        ['Subnets'][0]['AvailabilityZone'])

    # Otherwise, pick one.
    response = self.ec2.describe_availability_zones(
      Filters=[{'Name': 'region-name','Values': [self.region]}])
    for zone in response['AvailabilityZones']:
      if zone['State'] == 'available':
        return str(zone['ZoneName'])
    
    # If we reached here, we have a problem
    raise AWSSnapshotS3CopyException('No suitable availability zone found')


modules_manager.ModulesManager.RegisterModule(AWSSnapshotS3CopyCollector)
