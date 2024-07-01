# -*- coding: utf-8 -*-
"""Tests for the attribute containers."""

import unittest

import pandas
from dftimewolf.lib.containers import containers

CONTAINER_CLASSES = [
  containers.AWSS3Object,
  containers.AWSSnapshot,
  containers.AWSVolume,
  containers.DataFrame,
  containers.Directory,
  containers.File,
  containers.ForensicsVM,
  containers.FSPath,
  containers.GCEImage,
  containers.GCPLogs,
  containers.GCSObject,
  containers.GrrFlow,
  containers.Host,
  containers.OsqueryQuery,
  containers.OsqueryResult,
  containers.RemoteFSPath,
  containers.Report,
  containers.ThreatIntelligence,
  containers.TicketAttribute,
  containers.URL,
  containers.WorkspaceLogs,
  containers.YaraRule,
]

class ContainerTest(unittest.TestCase):
  """Tests relative to all containers."""

  def testHasContainerType(self):
    """Tests that all containers have a CONTAINER_TYPE attribute."""
    for container_class in CONTAINER_CLASSES:
      self.assertTrue(hasattr(container_class, 'CONTAINER_TYPE'))
      self.assertIsNotNone(
        container_class.CONTAINER_TYPE,
        msg=f'{container_class.__name__} has no defined CONTAINER_TYPE.')

class ReportDataTest(unittest.TestCase):
  """Tests for the Report data attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = containers.Report(module_name='name', text='text')

    expected_attribute_names = [
        'metadata', 'module_name', 'text', 'text_format']

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

    expected_attribute_names = ['indicator', 'metadata', 'name', 'path']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


class FSPathDataTest(unittest.TestCase):
  """Tests for the FSPath data attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = containers.FSPath(path='name')

    expected_attribute_names = ['metadata', 'path']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


class RemoteFSPathDataTest(unittest.TestCase):
  """Tests for the RemoteFSPath data attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = containers.RemoteFSPath(path='name', hostname='host')

    expected_attribute_names = ['hostname', 'metadata', 'path']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


class OsqueryQueryDataTest(unittest.TestCase):
  """Tests for the OsqueryQuery attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = containers.OsqueryQuery(
        query='', name='', description='', platforms=[],
        configuration_content='', configuration_path='')

    expected_attribute_names = [
        'configuration_content', 'configuration_path', 'description',
        'metadata', 'name', 'platforms', 'query',
    ]

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


class OsqueryResultDataTest(unittest.TestCase):
  """Tests for the OsqueryResult attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = containers.OsqueryResult(
        name='', description='', hostname='', query='',
        data_frame=pandas.DataFrame(), flow_identifier='', client_identifier='')

    expected_attribute_names = [
        'client_identifier', 'data_frame', 'description', 'flow_identifier',
        'hostname', 'metadata', 'name', 'query']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)

class TicketAttributeTest(unittest.TestCase):
  """Tests for the TicketAttribute attribute container."""
  def TestEquality(self):
    """Tests that the equality operator works as intended."""
    ticket_attribute_container_1 = containers.TicketAttribute(
      type_='type1', name='name1', value='value1')
    ticket_attribute_container_2 = containers.TicketAttribute(
      type_='type1', name='name2', value='value1')

    self.assertNotEqual(
      ticket_attribute_container_1, ticket_attribute_container_2)

    ticket_attribute_container_2.name = 'name1'

    self.assertEqual(ticket_attribute_container_1, ticket_attribute_container_2)

if __name__ == '__main__':
  unittest.main()
