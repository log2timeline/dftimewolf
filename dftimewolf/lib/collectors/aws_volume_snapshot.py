# Lint as: python3
"""AWS Volume snapshot collector."""

from typing import Optional, Any
import boto3

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class AWSVolumeSnapshotCollector(module.BaseModule):
  """Takes snapshots of AWS EBS volumes.

  Volume ID list can be passed in via SetUp args, or via AWSVolume containers
  from a previous module.

  Attributes:
    region: The region the volumes exist in.
  """

  def __init__(self,
      state: DFTimewolfState,
      name: Optional[str]=None,
      critical: Optional[bool] = False) -> None:
    """Initializes a AWSVolumeToS3 collector."""
    super(AWSVolumeSnapshotCollector, self).__init__(
        state, name=name, critical=critical)
    self.region: Any = ''

  # pylint: disable=arguments-differ
  def SetUp(self,
            volumes: str = '',
            region: str = '') -> None:
    """Sets up the AWSVolumeToS3 collector.

    Args:
      region (str): AWS region of the volumes.
    """
    self.region = region
    if volumes:
      for vol_id in volumes.split(','):
        self.state.StoreContainer(containers.AWSVolume(vol_id))

  def Process(self) -> None:
    """Images the volumes into S3."""

    volumes = [c.id for c in self.state.GetContainers(containers.AWSVolume)]
    if len(volumes) == 0:
      self.ModuleError('No volume IDs specified', critical=True)

    ec2 = boto3.client('ec2', region_name=self.region)
    try:
      # Describing volumes throws an exception if they don't exist.
      ec2.describe_volumes(VolumeIds=volumes)
    except ec2.exceptions.ClientError as exception:
      self.ModuleError('Error encountered describing volumes: {0!s}'.
        format(exception), critical=True)

    snapshot_ids = []
    try:
      # Snapshot taking is an asynchronous call, no need for threading
      self.logger.info('Taking snapshots of volumes {0:s}'.
        format(','.join(volumes)))
      for volume in volumes:
        response = ec2.create_snapshot(VolumeId=volume)
        snapshot_ids.append(response['SnapshotId'])

      self.logger.info('Waiting for snapshot completion')
      ec2.get_waiter('snapshot_completed').wait(SnapshotIds=snapshot_ids)
      self.logger.info('Snapshots complete: {0:s}'.
        format(','.join(snapshot_ids)))
    except ec2.exceptions.ClientError as exception:
      self.ModuleError('Error encountered snapshotting volumes: {0!s}'.
        format(exception), critical=True)

    for snap_id in snapshot_ids:
      self.state.StoreContainer(containers.AWSSnapshot(snap_id))


modules_manager.ModulesManager.RegisterModule(AWSVolumeSnapshotCollector)
