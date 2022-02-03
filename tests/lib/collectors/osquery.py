#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Osquery collector."""

import unittest

import mock

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.collectors import osquery
from dftimewolf.lib.containers.containers import OsqueryQuery
from dftimewolf.lib.errors import DFTimewolfError


class OsqueryCollectorTest(unittest.TestCase):
  """Tests for the GRR osquery collector."""

  def testInitialization(self) -> None:
    """Tests that the collector can be intialized."""
    test_state = state.DFTimewolfState(config.Config)
    osquery_collector = osquery.OsqueryCollector(test_state)
    self.assertIsNotNone(osquery_collector)

  def testSetup(self) -> None:
    """Tests the collector's Setup() function."""
    test_state = state.DFTimewolfState(config.Config)
    osquery_collector = osquery.OsqueryCollector(test_state)

    with self.assertRaises(DFTimewolfError) as context:
      osquery_collector.SetUp(query='', paths='')

    self.assertEqual(
        context.exception.message, 'Both query and paths cannot be empty.')

  def testSetupQuery(self) -> None:
    """Tests the collector's Setup() function with invalid query parameter."""
    test_state = state.DFTimewolfState(config.Config)
    osquery_collector = osquery.OsqueryCollector(test_state)

    with self.assertRaises(DFTimewolfError) as context:
      osquery_collector.SetUp(query='not a query', paths='')

    self.assertEqual(context.exception.message, 'No valid osquery collected.')

  def testSetupPaths(self) -> None:
    """Tests the collector's Setup() method with invalid paths parameter."""
    test_state = state.DFTimewolfState(config.Config)
    osquery_collector = osquery.OsqueryCollector(test_state)

    test_empty_data = ""
    test_bad_data = "bad"

    with mock.patch(
        'builtins.open',
        new=mock.mock_open(read_data=test_empty_data)) as _:
      with self.assertRaises(DFTimewolfError) as context:
        osquery_collector.SetUp(query='', paths='empty')

    self.assertEqual(context.exception.message, 'No valid osquery collected.')

    with mock.patch(
        'builtins.open',
        new=mock.mock_open(read_data=test_bad_data)) as _:
      with self.assertRaises(DFTimewolfError) as context:
        osquery_collector.SetUp(query='', paths='fbad')

    self.assertEqual(context.exception.message, 'No valid osquery collected.')

  @mock.patch('os.path.exists')
  def testProcess(self, mock_exists) -> None:
    """Tests the collector's Process() function."""
    test_state = state.DFTimewolfState(config.Config)
    osquery_collector = osquery.OsqueryCollector(test_state)
    mock_exists.return_value = True

    test_ok_data = "SELECT * FROM processes"

    with mock.patch(
        'builtins.open',
        new=mock.mock_open(read_data=test_ok_data)) as _:
      osquery_collector.SetUp(query='', paths='ok')

    osquery_collector.Process()

    containers = test_state.GetContainers(OsqueryQuery)
    self.assertEqual(len(containers), 1)


if __name__ == '__main__':
  unittest.main()
