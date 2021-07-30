#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the aws container interface."""

import unittest

from dftimewolf.lib.containers import aws_containers


class AWSAttributeContainerTest(unittest.TestCase):
  """Tests for the attribute container interface."""

  def testSetVolumesIDs(self):
    """Tests the SetVolumes function."""
    container = aws_containers.AWSAttributeContainer()
    volumes=['vol-01234567', 'vol-12345678']
    container.SetVolumeIDs(volumes)

    self.assertEqual(volumes, container.volumes)

  def testSetSnapshotIDs(self):
    """Tests the SetSnapshots function."""
    container = aws_containers.AWSAttributeContainer()
    snapshots=['snap-01234567', 'snap-12345678']
    container.SetSnapshotIDs(snapshots)

    self.assertEqual(snapshots, container.snapshots)

  def testAppendS3Path(self):
    """Tests the AppendS3Path function."""
    container = aws_containers.AWSAttributeContainer()
    paths=['s3://bucket/path/one', 's3://bucket/path/two']

    for path in paths:
      container.AppendS3Path(path)

    self.assertEqual(paths, container.s3_paths)

if __name__ == '__main__':
  unittest.main()
