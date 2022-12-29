#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Azure logging collector."""

import unittest
from unittest import mock

from azure.core import exceptions as az_exceptions

from dftimewolf.lib import state
from dftimewolf import config
from dftimewolf.lib.collectors import azure_logging
from dftimewolf.lib.containers import containers
from dftimewolf.lib import errors


class AzureLogging(unittest.TestCase):
  """Tests for the Azure logging collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    azure_logging_collector = azure_logging.AzureLogsCollector(test_state)
    self.assertIsNotNone(azure_logging_collector)

  # pylint: disable=protected-access
  def testSetup(self):
    """Tests that attributes are properly set during setup."""
    test_state = state.DFTimewolfState(config.Config)
    azure_logging_collector = azure_logging.AzureLogsCollector(test_state)
    azure_logging_collector.SetUp(
        subscription_id='55c5ff71-b3e2-450d-89da-cb12c1a38d87',
        filter_expression='eventTimestamp ge \'2022-02-01\'',
        profile_name='profile1')
    self.assertEqual(
        azure_logging_collector._subscription_id,
        '55c5ff71-b3e2-450d-89da-cb12c1a38d87')
    self.assertEqual(
        azure_logging_collector._filter_expression,
        'eventTimestamp ge \'2022-02-01\'')
    self.assertEqual(
        azure_logging_collector._profile_name, 'profile1')

  @mock.patch('libcloudforensics.providers.azure.internal.common.GetCredentials')  # pylint: disable=line-too-long
  @mock.patch('azure.mgmt.monitor.MonitorManagementClient')
  def testProcess(self, mock_monitor, mock_credentials):
    """Tests that the Azure monitor client is called with the correct args."""

    # Create mock objects with required attributes - not mocking Azure objects
    # directly as this leads to frail mocks based on version-dependent package
    # names like azure.mgmt.monitor.v2015_04_01.models._models_py3.EventData.
    mock_monitor_client = mock.MagicMock(spec=['activity_logs'])
    mock_activity_logs_client = mock.MagicMock(spec=['list'])
    mock_event_data = mock.MagicMock(spec=['as_dict'])

    mock_monitor_client.activity_logs = mock_activity_logs_client
    mock_activity_logs_client.list.return_value = iter([mock_event_data])
    mock_event_data.as_dict.return_value = {'log_entry': 1}

    mock_monitor.return_value = mock_monitor_client
    mock_credentials.return_value = ('_', 'Credentials')

    test_state = state.DFTimewolfState(config.Config)
    azure_logging_collector = azure_logging.AzureLogsCollector(test_state)

    azure_logging_collector.SetUp(
        subscription_id='55c5ff71-b3e2-450d-89da-cb12c1a38d87',
        filter_expression='eventTimestamp ge \'2022-02-01\'')
    azure_logging_collector.Process()

    mock_monitor.assert_called_with(
        'Credentials', '55c5ff71-b3e2-450d-89da-cb12c1a38d87')
    mock_activity_logs_client.list.assert_called_with(
        filter='eventTimestamp ge \'2022-02-01\'')

    azure_containers = azure_logging_collector.GetContainers(containers.File)
    self.assertTrue(azure_containers)
    self.assertEqual(azure_containers[0].name, 'AzureLogsCollector result')

    # Ensure DFTimewolfError is raised when creds aren't found.
    mock_credentials.side_effect = FileNotFoundError
    with self.assertRaises(errors.DFTimewolfError):
      azure_logging_collector.Process()
    mock_credentials.side_effect = None

    # Ensure DFTimewolfError is raised when Azure libs raise an exception.
    mock_activity_logs_client.list.side_effect = (
        az_exceptions.HttpResponseError)
    with self.assertRaises(errors.DFTimewolfError):
      azure_logging_collector.Process()
