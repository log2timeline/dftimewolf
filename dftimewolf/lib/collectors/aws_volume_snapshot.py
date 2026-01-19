# Lint as: python3
"""AWS Volume snapshot collector."""

from typing import Optional, Any, Callable
import boto3

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import cache
from dftimewolf.lib import telemetry
from dftimewolf.lib.containers import manager as container_manager


class AWSVolumeSnapshotCollector(module.BaseModule):
  """Takes snapshots of AWS EBS volumes.

  Volume ID list can be passed in via SetUp args, or via AWSVolume containers
  from a previous module.

  Attributes:
    region: The region the volumes exist in.
  """

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initializes a AWSVolumeToS3 collector."""
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)

    self.region: Any = ''

  # pylint: disable=arguments-differ
  def SetUp(self,
            volumes: Optional[str] = '',
            region: str = '') -> None:
    """Sets up the AWSVolumeToS3 collector.

    Args:
      region (str): AWS region of the volumes.
    """
    self.region = region
    if volumes:
      for vol_id in volumes.split(','):
        self.StoreContainer(containers.AWSVolume(vol_id))

  def Process(self) -> None:
    """Images the volumes into S3."""

    volumes = [c.id for c in self.GetContainers(containers.AWSVolume)]
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
      self.logger.info(f'Taking snapshots of volumes {",".join(volumes):s}')
      for volume in volumes:
        response = ec2.create_snapshot(VolumeId=volume)
        snapshot_ids.append(response['SnapshotId'])

      self.logger.debug("Waiting for snapshot completion")
      ec2.get_waiter('snapshot_completed').wait(SnapshotIds=snapshot_ids)
      self.logger.info(f'Snapshots complete: {",".join(snapshot_ids):s}')
    except ec2.exceptions.ClientError as exception:
      self.ModuleError('Error encountered snapshotting volumes: {0!s}'.
        format(exception), critical=True)

    for snap_id in snapshot_ids:
      self.StoreContainer(containers.AWSSnapshot(snap_id))


modules_manager.ModulesManager.RegisterModule(AWSVolumeSnapshotCollector)
