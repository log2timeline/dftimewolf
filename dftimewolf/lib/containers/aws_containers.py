# -*- coding: utf-8 -*-
"""AWS specific containers."""

from dftimewolf.lib.containers import interface


class AWSAttributeContainer(interface.AttributeContainer):
  """Attribute container definition for AWS resources.

  Attributes:
    snapshots (list[str]): List of snapshot IDs.
    volumes (list[str]): List of volume IDs.
  """
  CONTAINER_TYPE = 'awsattributelist'

  def __init__(self):
    """Initializes the AWSAttributeContainer"""
    super(AWSAttributeContainer, self).__init__()
    self.snapshots = None
    self.volumes = None
    self.s3_paths = []

  def SetSnapshotIDs(self, snapshot_ids):
    """Sets the snapshot ids list.

    Args:
      snapshot_ids (List[str]): The list of snapshot IDs.
    """
    self.snapshots = snapshot_ids

  def SetVolumeIDs(self, volume_ids):
    """Sets the volume ids list.

    Args:
      volume_ids (List[str]): The list of volume IDs.
    """
    self.volumes = volume_ids

  def AppendS3Path(self, path):
    """Append a value to a list of S3 paths.

    Args:
      path (str): The S3 path to append.
    """
    if not path.startswith('s3://'):
      path = 's3://' + path
    self.s3_paths.append(path)
