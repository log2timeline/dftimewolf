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

class GCSObjectListTest(unittest.TestCase):
  """Tests for the GCSObjectList container."""

  def testGCSObjectListSetAndGet(self):
    """Tests the setting and retrival of attributes."""
    paths_without_prefix = [
      'fake-bucket/object-1',
      'fake-bucket/object-2',
      'fake-bucket/object-3',
    ]
    paths_with_prefix = ['gs://' + path for path in paths_without_prefix]

    container = containers.GCSObjectList()
    self.assertEqual(['object_list'], sorted(container.GetAttributeNames()))

    container = containers.GCSObjectList(paths_with_prefix)
    self.assertEqual(sorted(paths_with_prefix), sorted(container.object_list))

    container = containers.GCSObjectList(paths_without_prefix)
    self.assertEqual(sorted(paths_with_prefix), sorted(container.object_list))


if __name__ == '__main__':
  unittest.main()
