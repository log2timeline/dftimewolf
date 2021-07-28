# Lint as: python3
"""Copies AWS EBS snapshots into AWS S3."""

import io
import os
import re
import subprocess
import tempfile

from dftimewolf.lib import module
from dftimewolf.lib.containers import aws_containers
from dftimewolf.lib.modules import manager as modules_manager


class AWSSnapshotS3CopyCollector(module.BaseModule):
  """Copies AWS EBS snapshots into AWS S3.

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

  # pylint: disable=arguments-differ
  def SetUp(self,
            snapshots=None,
            bucket=None,
            region=None):
    """Sets up the AWSVolumeToS3 collector.

    Args:
      snapshots (str): Comma seperated list of snapshot IDs. If not specified,
        will look for an AWS snapshot list container for state from a previous
        module.
      bucket (str): Th edestination s3 bucket. 
    """
    self.snapshots = snapshots
    self.bucket = bucket

  def Process(self):
    """Images the volumes into S3."""
    for attribute in self.state.GetContainers(aws_containers.AWSAttributeContainer):
      print('----------------------------')
      print(attribute.snapshots)
      print(attribute.volumes)


modules_manager.ModulesManager.RegisterModule(AWSSnapshotS3CopyCollector)
