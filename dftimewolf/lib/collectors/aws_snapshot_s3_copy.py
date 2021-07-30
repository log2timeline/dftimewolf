# Lint as: python3
"""Copies AWS EBS snapshots into AWS S3."""

import threading
from time import sleep
import boto3

from libcloudforensics.providers.aws import forensics
from libcloudforensics.errors import ResourceCreationError
from dftimewolf.lib import module
from dftimewolf.lib.containers import aws_containers
from dftimewolf.lib.modules import manager as modules_manager

class AWSSnapshotS3CopyCollector(module.BaseModule):
  """Copies AWS EBS snapshots into AWS S3. Snapshot list can be passed in via
  SetUp parameters, or from a AWSAttributeContainer from a previous module.

  Attributes:
    snapshots: The snapshots to copy.
    bucket: The destination S3 bucket.
  """

  def __init__(self, state, name=None, critical=False):
    """Initializes a AWSVolumeToS3 collector."""
    super(AWSSnapshotS3CopyCollector, self).__init__(
        state, name=name, critical=critical)
    self.snapshots = None
    self.bucket = None
    self.region = None
    self.subnet = None
    self._lock = threading.Lock()

  # pylint: disable=arguments-differ
  def SetUp(self,
            snapshots=None,
            bucket=None,
            region=None,
            subnet=None):
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

  def Process(self):
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

    ec2 = boto3.client('ec2', region_name=self.region)
    try:
      ec2.describe_snapshots(SnapshotIds=self.snapshots)
      zone = self._PickAvailabilityZone(ec2, self.subnet)
    except ec2.exceptions.ClientError as exception:
      self.ModuleError('Error encountered describing snapshots: {0!s}'.\
        format(exception), critical=True)

    threads = []
    self.logger.info(
      'Starting {0:d} copy threads, expect log messages from each'\
        .format(len(self.snapshots)))
    for snapshot in self.snapshots:
      try:
        thread = threading.Thread(
          target=self._PerformCopyThread, args=(snapshot, zone))
        thread.start()
        threads.append(thread)
        sleep(2) # Offest each thread start slightly
      except ResourceCreationError as exception:
        self.ModuleError('Exception during copy operation: {0!s}'\
          .format(exception), critical=True)

    for thread in threads:
      thread.join()

    self.logger.info('Snapshot copy complete: {0:s}'\
      .format(','.join(self.state.GetContainers(\
        aws_containers.AWSAttributeContainer)[0].s3_paths)))


  def _PerformCopyThread(self, snapshot_id, zone):
    """Perform the copy operation. Designed to be called as a new thread from
    Process(). Will place the output file paths into the state container,
    (creating it if it doesn't exist already.)

    Args:
      snapshot_id (str): The snapshot ID.
      zone (str): The AWS availability zone."""
    forensics.CopyEBSSnapshotToS3(
      self.bucket,
      snapshot_id,
      'ebsCopy',
      zone,
      subnet_id=self.subnet)

    # Copy operation puts the image in bucket/snapshot
    files = ['image.bin', 'log.txt', 'hlog.txt', 'mlog.txt']
    output = ['s3://{0:s}/{1:s}/{2:s}'.format(self.bucket, snapshot_id, file)
      for file in files]

    with self._lock:
      if len(self.state.GetContainers(aws_containers.AWSAttributeContainer)):
        for path in output:
          self.state.GetContainers(aws_containers.AWSAttributeContainer)[0]\
            .AppendS3Path(path)
      else:
        container = aws_containers.AWSAttributeContainer()
        for path in output:
          container.AppendS3Path(path)
        self.state.StoreContainer(container)

  # pylint: disable=inconsistent-return-statements
  def _PickAvailabilityZone(self, ec2, subnet=None) -> str:
    """Given a region + subnet, pick an availability zone. If the subnet is
    provided, it's AZ is returned. Otherwise, one is picked from those
    available in the region.

    Args:
      ec2 (boto3.client): EC2 client.
      subnet (str): Optional. An EC2 subnet ID.

    Returns:
      A string representing the AZ."""
    # If we received a subnet ID, return the AZ for it
    if subnet:
      return str(ec2.describe_subnets(SubnetIds=[subnet])\
        ['Subnets'][0]['AvailabilityZone'])

    # Otherwise, pick one.
    response = ec2.describe_availability_zones(
      Filters=[{'Name': 'region-name','Values': [self.region]}])
    for zone in response['AvailabilityZones']:
      if zone['State'] == 'available':
        return str(zone['ZoneName'])

modules_manager.ModulesManager.RegisterModule(AWSSnapshotS3CopyCollector)
