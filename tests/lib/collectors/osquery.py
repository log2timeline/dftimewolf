#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Osquery collector."""

import json
import unittest

import mock

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.collectors import osquery
from dftimewolf.lib.containers.containers import OsqueryQuery
from dftimewolf.lib.errors import DFTimewolfError


class OsqueryCollectorTest(unittest.TestCase):
  """Tests for the GRR osquery collector."""

  def setUp(self) -> None:
    super().setUp()
    test_state = state.DFTimewolfState(config.Config)
    self.osquery_collector = osquery.OsqueryCollector(test_state)

  def testInitialization(self) -> None:
    """Tests that the collector can be initialized."""
    self.assertEqual(self.osquery_collector.osqueries, [])
    self.assertEqual(self.osquery_collector.configuration_content, '')
    self.assertEqual(self.osquery_collector.configuration_path, '')
    self.assertEqual(self.osquery_collector.file_collection_columns, [])

  def testSetupError(self) -> None:
    """Tests the collector's Setup() function with invalid query, path."""
    with self.assertRaises(DFTimewolfError) as context:
      self.osquery_collector.SetUp(query='', paths='')

    self.assertEqual(
        context.exception.message, 'Both query and paths cannot be empty.')

  def testSetupQueryError(self) -> None:
    """Tests the collector's Setup() function with invalid query parameter."""
    with self.assertRaises(DFTimewolfError) as context:
      self.osquery_collector.SetUp(query='not a query', paths='')

    self.assertEqual(context.exception.message, 'No valid osquery collected.')

    with self.assertRaises(DFTimewolfError) as context:
      self.osquery_collector.SetUp(query='SELECT * FROM processes', paths='')

    self.assertEqual(context.exception.message, 'No valid osquery collected.')

  def testSetupPathsError(self) -> None:
    """Tests the collector's Setup() method with invalid paths parameter."""
    test_empty_data = ""
    test_bad_data = "bad"

    with mock.patch(
        'builtins.open',
        new=mock.mock_open(read_data=test_empty_data)) as _:
      with self.assertRaises(DFTimewolfError) as context:
        self.osquery_collector.SetUp(query='', paths='empty')

    self.assertEqual(context.exception.message, 'No valid osquery collected.')

    with mock.patch(
        'builtins.open',
        new=mock.mock_open(read_data=test_bad_data)) as _:
      with self.assertRaises(DFTimewolfError) as context:
        self.osquery_collector.SetUp(query='', paths='fbad')

    self.assertEqual(context.exception.message, 'No valid osquery collected.')

  def testSetUpConfigurationError(self) -> None:
    """Tests the collector's SetUp() function with invalid configuration."""
    with self.assertRaises(DFTimewolfError) as context:
      self.osquery_collector.SetUp(
          query='SELECT * FROM processes;', paths='',
          configuration_content='test', remote_configuration_path='test')
    self.assertEqual(
        context.exception.message,
        'Only one configuration argument can be set.')

    with self.assertRaises(DFTimewolfError) as context:
      self.osquery_collector.SetUp(
          query='SELECT * FROM processes;', paths='',
          local_configuration_path ='test', remote_configuration_path='test')
    self.assertEqual(
        context.exception.message,
        'Only one configuration argument can be set.')

    with self.assertRaises(DFTimewolfError) as context:
      self.osquery_collector.SetUp(
          query='SELECT * FROM processes;', paths='',
          local_configuration_path ='test', configuration_content='test')
    self.assertEqual(
        context.exception.message,
        'Only one configuration argument can be set.')

    with self.assertRaises(DFTimewolfError) as context:
      self.osquery_collector.SetUp(
          query='SELECT * from processes;', paths='',
          configuration_content='invalid content')
    self.assertEqual(
        context.exception.message,
        'Osquery configuration does not contain valid JSON.')

  def testSetUpRemoteConfigurationPath(self) -> None:
    """Tests the collector's SetUp() function with the remote config path."""
    self.osquery_collector.SetUp(
        query='SELECT * from test;',
        paths='ok',
        remote_configuration_path='/test/path')
    self.assertEqual(self.osquery_collector.configuration_path, '/test/path')

  def testSetUpLocalConfigurationPath(self) -> None:
    """Tests the collector's SetUp() function with the local config path."""
    with mock.patch(
        'builtins.open',
        new=mock.mock_open(read_data='{"test": "test"}')) as _:
      self.osquery_collector.SetUp(
          query='SELECT * from test;',
          paths='ok',
          local_configuration_path='test')
    self.assertEqual(
        self.osquery_collector.configuration_content, '{"test": "test"}')

  def testSetUpConfigurationContent(self) -> None:
    """Tests the collector's SetUp() function with configuration content."""
    self.osquery_collector.SetUp(
        query='SELECT * from test;',
        paths='ok',
        configuration_content='{"test": "test"}')
    self.assertEqual(
        self.osquery_collector.configuration_content, '{"test": "test"}')

  def testSetUpFileCollectionColumns(self) -> None:
    """Tests the collector's SetUp() function with file collection columns."""
    self.osquery_collector.SetUp(
        query='SELECT * from test;',
        paths='ok',
        file_collection_columns='a,b')
    self.assertEqual(
        self.osquery_collector.file_collection_columns, ['a', 'b'])

  @mock.patch('os.path.exists')
  def testProcessTextFile(self, mock_exists) -> None:
    """Tests the collector's Process() function with a text file."""
    mock_exists.return_value = True

    test_ok_data = "SELECT * FROM processes;"

    with mock.patch(
        'builtins.open',
        new=mock.mock_open(read_data=test_ok_data)) as _:
      self.osquery_collector.SetUp(query='', paths='ok')

    self.osquery_collector.Process()

    containers = self.osquery_collector.GetContainers(OsqueryQuery)
    self.assertEqual(len(containers), 1)
    self.assertEqual(containers[0].query, "SELECT * FROM processes;")
    self.assertEqual(containers[0].configuration_content, '')
    self.assertEqual(containers[0].configuration_path, '')

  @mock.patch('os.path.exists')
  def testProcessQueryPack(self, mock_exists) -> None:
    """Tests the collector's Process() function with a Osquery Pack file."""
    mock_exists.return_value = True

    test_ok_data = json.dumps({
        "platform": "darwin",
        "queries": {
            "query_1": {
                "query":
                "select * from launchd where path like '%System.plist';",
                "interval": "3600",
                "version": "1.4.5",
                "description": "description",
                "value": "Artifact used by this malware"
            },
            "query_2": {
                "query": "select * from test where path like '%user32.dll';",
                "interval": "3600",
                "version": "1.4.5",
                "platform": "windows",
                "description": "description",
                "value": "Artifact used by this malware"
            }
        }
    }, indent=4)

    with mock.patch(
        'builtins.open',
        new=mock.mock_open(read_data=test_ok_data)) as _:
      self.osquery_collector.SetUp(query='', paths='ok.json')

    self.osquery_collector.Process()

    containers = self.osquery_collector.GetContainers(OsqueryQuery)
    self.assertEqual(len(containers), 2)

    self.assertEqual(containers[0].name, 'query_1')
    self.assertEqual(containers[0].description, 'description')
    self.assertEqual(containers[0].platforms, ['darwin'])
    self.assertEqual(containers[0].query,
                     'select * from launchd where path like \'%System.plist\';')

    self.assertEqual(containers[1].name, 'query_2')
    self.assertEqual(containers[1].description, 'description')
    self.assertEqual(containers[1].platforms, ['windows'])
    self.assertEqual(containers[1].query,
                     'select * from test where path like \'%user32.dll\';')


if __name__ == '__main__':
  unittest.main()
