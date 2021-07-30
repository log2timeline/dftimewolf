# Lint as: python3
"""AWS Volume snapshot collector."""

import boto3

from dftimewolf.lib import module
from dftimewolf.lib.containers import aws_containers
from dftimewolf.lib.modules import manager as modules_manager


class AWSVolumeSnapshotCollector(module.BaseModule):
  """Takes snapshots of AWS EBS volumes. Volume ID list can be passed in via
  SetUp args, or from a AWSAttributeContainer from a previous module.

  Attributes:
    volumes: The volumes to copy.
    region: The region the volumes exist in.
  """

  def __init__(self, state, name=None, critical=False):
    """Initializes a AWSVolumeToS3 collector."""
    super(AWSVolumeSnapshotCollector, self).__init__(
        state, name=name, critical=critical)
    self.volumes = None
    self.region = None

  # pylint: disable=arguments-differ
  def SetUp(self,
            volumes=None,
            region=None):
    """Sets up the AWSVolumeToS3 collector.

    Args:
      volumes (str): Comma seperated list of volume IDs.
      region (str): AWS region of the volumes.
    """
    # Usually we'd validate the volumes exist here - But they can be passed in
    # as argument here, or via a container from a previous module. SetUp runs
    # simultaneously across all modules, so state is not available yet. We'll
    # have to check it in Process. :(
    self.volumes = volumes
    self.region = region

  def Process(self):
    """Images the volumes into S3."""
    # The list of volumes could have been set in SetUp, or it might come from a
    # container from a previous module. Check where they come from, and
    # validate them.
    if self.volumes:
      self.volumes = self.volumes.split(',')
    elif len(self.state.GetContainers(aws_containers.AWSAttributeContainer)):
      self.volumes = self.state.GetContainers(
        aws_containers.AWSAttributeContainer)[0].volumes
    else:
      self.ModuleError('No volume IDs specified', critical=True)

    ec2 = boto3.client('ec2', region_name=self.region)
    try:
      ec2.describe_volumes(VolumeIds=self.volumes)
    except ec2.exceptions.ClientError as exception:
      self.ModuleError('Error encountered describing volumes: {0!s}'.\
        format(exception), critical=True)

    snapshot_ids = []
    try:
      # Snapshot taking is an asynchronous call, no need for threading
      self.logger.info('Taking snapshots of volumes {0:s}'\
        .format(','.join(self.volumes)))
      for volume in self.volumes:
        response = ec2.create_snapshot(VolumeId=volume)
        snapshot_ids.append(response['SnapshotId'])

      self.logger.info('Waiting for snapshot completion')
      ec2.get_waiter('snapshot_completed').wait(SnapshotIds=snapshot_ids)
      self.logger.info('Snapshots complete: {0:s}'\
        .format(','.join(snapshot_ids)))
    except ec2.exceptions.ClientError as exception:
      self.ModuleError('Error encountered snapshotting volumes: {0!s}'.\
        format(exception), critical=True)

    # Set the state
    if len(self.state.GetContainers(aws_containers.AWSAttributeContainer)):
      self.state.GetContainers(aws_containers.AWSAttributeContainer)[0]\
        .SetSnapshotIDs(snapshot_ids)
    else:
      container = aws_containers.AWSAttributeContainer()
      container.SetSnapshotIDs(snapshot_ids)
      self.state.StoreContainer(container)

modules_manager.ModulesManager.RegisterModule(AWSVolumeSnapshotCollector)
