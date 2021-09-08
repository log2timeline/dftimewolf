# -*- coding: utf-8 -*-
"""Tests for the attribute containers."""

import unittest

from dftimewolf.lib.containers import containers

class ReportDataTest(unittest.TestCase):
  """Tests for the Report data attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = containers.Report(module_name='name', text='text')

    expected_attribute_names = [
        'attributes', 'module_name', 'text', 'text_format']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


class ThreatIntelligenceDataTest(unittest.TestCase):
  """Tests for the threat intelligence data attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = containers.ThreatIntelligence(
        name='name',
        indicator='.*',
        path='/')

    expected_attribute_names = ['indicator', 'name', 'path']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


class FSPathDataTest(unittest.TestCase):
  """Tests for the FSPath data attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = containers.FSPath(path='name')

    expected_attribute_names = ['path']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


class RemoteFSPathDataTest(unittest.TestCase):
  """Tests for the RemoteFSPath data attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = containers.RemoteFSPath(path='name', hostname='host')

    expected_attribute_names = ['hostname', 'path']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)

class S3VolumeImageContainerTest(unittest.TestCase):
  """Tests for the attribute container interface."""

  def testAppendS3Image(self):
    """Tests the AppendS3Path function."""
    image_path = 's3://bucket/path/image.bin'
    hash_paths=[
      's3://bucket/path/log.txt',
      's3://bucket/path/hlog.txt',
      's3://bucket/path/mlog.txt']
    container = containers.S3VolumeImage(image_path, hash_paths)

    image_path_no_prefix = 'bucket/path/image.bin'
    hash_paths_no_prefix = [
      'bucket/path/log.txt',
      'bucket/path/hlog.txt',
      'bucket/path/mlog.txt']
    no_prefix_container = containers.S3VolumeImage(image_path, hash_paths)

    self.assertEqual(no_prefix_container, container)

if __name__ == '__main__':
  unittest.main()
