# -*- coding: utf-8 -*-
"""Tests for the attribute containers."""

import unittest

import pandas
from dftimewolf.lib.containers import containers

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
        query='', name='', description='', platforms=[])

    expected_attribute_names = [
        'description', 'metadata', 'name', 'platforms', 'query']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


class OsqueryResultDataTest(unittest.TestCase):
  """Tests for the OsqueryResult attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = containers.OsqueryResult(
        name='', description='', hostname='', query=''
        data_frame=pandas.DataFrame(), flow_identifier='', client_identifier='')

    expected_attribute_names = [
        'client_identifier', 'data_frame', 'description', 'flow_identifier',
        'hostname', 'metadata', 'name', 'query']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


if __name__ == '__main__':
  unittest.main()
