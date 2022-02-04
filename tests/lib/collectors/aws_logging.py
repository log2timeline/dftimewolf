#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the AWS logging collector."""

import unittest
import unittest.mock as mock
from datetime import datetime as dt

from dftimewolf.lib import state
from dftimewolf import config
from dftimewolf.lib.collectors import aws_logging
from dftimewolf.lib.containers.containers import AWSLogs


class AWSLoggingTest(unittest.TestCase):
  """Tests for the AWS logging collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    aws_logging_collector = aws_logging.AWSLogsCollector(test_state)
    self.assertIsNotNone(aws_logging_collector)

  def testSetup(self):
    """Tests that attributes are properly set during setup."""
    test_state = state.DFTimewolfState(config.Config)
    aws_logging_collector = aws_logging.AWSLogsCollector(test_state)
    aws_logging_collector.SetUp(
        'fake-zone-1b',
        profile_name='default',
        query_filter='Username,fakename',
        start_time='2021-01-01 00:00:00',
        end_time='2021-01-02 00:00:00')

    # pylint: disable=protected-access
    self.assertEqual(aws_logging_collector._zone, 'fake-zone-1b')
    self.assertEqual(aws_logging_collector._profile_name, 'default')
    self.assertEqual(aws_logging_collector._query_filter, 'Username,fakename')
    self.assertEqual(
        aws_logging_collector._start_time,
        dt.fromisoformat('2021-01-01 00:00:00'))
    self.assertEqual(
      aws_logging_collector._end_time,
      dt.fromisoformat('2021-01-02 00:00:00'))

  @mock.patch('boto3.session.Session')
  def testProcess(self, mock_boto3):
    """Tests the process method."""
    mock_session = mock.MagicMock(spec=['client'])
    mock_client = mock.MagicMock(spec=['lookup_events'])
    mock_client.lookup_events.return_value = {'Events': [{'log_line':1}]}
    mock_session.client.return_value = mock_client
    mock_boto3.return_value = mock_session

    test_state = state.DFTimewolfState(config.Config)
    aws_logging_collector = aws_logging.AWSLogsCollector(test_state)

    aws_logging_collector.SetUp(
        'fake-zone-1b',
        query_filter='Username,fakename',
        start_time='2021-01-01 00:00:00',
        end_time='2021-01-02 00:00:00')
    aws_logging_collector.Process()

    mock_session.client.assert_called_with('cloudtrail')
    mock_client.lookup_events.assert_called_with(
        LookupAttributes=[
          {
            'AttributeKey': 'Username',
            'AttributeValue': 'fakename'
          }
        ],
        StartTime=dt.fromisoformat('2021-01-01 00:00:00'),
        EndTime=dt.fromisoformat('2021-01-02 00:00:00'))
    self.assertTrue(test_state.GetContainers(AWSLogs))


if __name__ == '__main__':
  unittest.main()
