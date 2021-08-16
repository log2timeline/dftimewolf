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

  def testAppendS3Image(self):
    """Tests the AppendS3Path function."""
    container = aws_containers.AWSAttributeContainer()
    image_path = 's3://bucket/path/image.bin'
    hash_paths=[
      's3://bucket/path/log.txt',
      's3://bucket/path/hlog.txt',
      's3://bucket/path/mlog.txt']

    image_path_no_prefix = 'bucket/path/image.bin'
    hash_paths_no_prefix = [
      'bucket/path/log.txt',
      'bucket/path/hlog.txt',
      'bucket/path/mlog.txt']

    container.AppendS3Image(aws_containers.S3Image(image_path, hash_paths))
    self.assertEqual(aws_containers.S3Image(image_path, hash_paths),
        container.s3_images[0])

    container = aws_containers.AWSAttributeContainer()
    container.AppendS3Image(aws_containers.S3Image(
        image_path_no_prefix, hash_paths_no_prefix))
    self.assertEqual(aws_containers.S3Image(image_path, hash_paths),
        container.s3_images[0])


if __name__ == '__main__':
  unittest.main()
