#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the AWS logging collector."""

import unittest
from datetime import datetime as dt

import mock

from dftimewolf.lib import state
from dftimewolf import config
from dftimewolf.lib.collectors import aws_logging
from dftimewolf.lib.containers.containers import AWSLogs


class AWSLoggingTest(unittest.TestCase):
  """Tests for the AWS logging collector."""

  FAKE_ZONE = 'fake-zone-1b'
  FAKE_LCF_RESPONSE = [
    {
      'EventName': 'GetCallerIdentity',
      'ReadOnly': 'true',
      'AccessKeyId': '11111111111111111111',
      'EventTime': dt.fromisoformat('2021-01-01 00:00:00'),
      'EventSource': 'sts.amazonaws.com',
      'Username': 'fakename',
      'Resources': [],
      'CloudTrailEvent': '{}'
    },
    {
      'EventName': 'GetCallerIdentity',
      'ReadOnly': 'true',
      'AccessKeyId': '11111111111111111111',
      'EventTime': dt.fromisoformat('2021-01-01 00:00:00'),
      'EventSource': 'sts.amazonaws.com',
      'Username': 'fakename',
      'Resources': [],
      'CloudTrailEvent': '{}'
    }
  ]

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    aws_logging_collector = aws_logging.AWSLogsCollector(test_state)
    self.assertIsNotNone(aws_logging_collector)

  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount')
  @mock.patch('libcloudforensics.providers.aws.internal.log.AWSCloudTrail')
  # pylint: disable=unused-argument
  def testLogClientArgs(self, mock_log, mock_account):
    """Tests that libcloudforensics methods are called with the correct
    args.
    """
    test_state = state.DFTimewolfState(config.Config)
    aws_logging_collector = aws_logging.AWSLogsCollector(test_state)

    aws_logging_collector.SetUp(self.FAKE_ZONE,
        query_filter='Username,fakename',
        start_time='2021-01-01 00:00:00',
        end_time='2021-01-02 00:00:00')
    aws_logging_collector.Process()

    # pylint: disable=protected-access,no-member
    aws_logging_collector._log_client.LookupEvents.assert_called_with(
        qfilter='Username,fakename',
        starttime=dt.fromisoformat('2021-01-01 00:00:00'),
        endtime=dt.fromisoformat('2021-01-02 00:00:00'))

  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount')
  @mock.patch('libcloudforensics.providers.aws.internal.log.'
      'AWSCloudTrail.LookupEvents', return_value=FAKE_LCF_RESPONSE)
  # pylint: disable=unused-argument
  def testContainers(self, mock_log, mock_account):
    """Tests that the containers are added to state."""
    test_state = state.DFTimewolfState(config.Config)
    aws_logging_collector = aws_logging.AWSLogsCollector(test_state)

    aws_logging_collector.SetUp(self.FAKE_ZONE)
    aws_logging_collector.Process()

    self.assertTrue(test_state.GetContainers(AWSLogs))


if __name__ == '__main__':
  unittest.main()
