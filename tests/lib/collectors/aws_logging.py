#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the AWS logging collector."""

import unittest
from datetime import datetime as dt

import mock

from dftimewolf.lib import state
from dftimewolf import config
from dftimewolf.lib.collectors import aws_logging

class AWSLoggingTest(unittest.TestCase):
  """Tests for the AWS logging collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    aws_logging_collector = aws_logging.AWSLogsCollector(test_state)
    self.assertIsNotNone(aws_logging_collector)

  @mock.patch('libcloudforensics.providers.aws.internal.account.AWSAccount',
      autospec=True)
  @mock.patch('libcloudforensics.providers.aws.internal.log.AWSCloudTrail',
      autospec=True)
  # pylint: disable=unused-argument
  def testLogClientArgs(self, mock_log, mock_account):
    """Tests that libcloudforensics methods are called with the correct
    args.
    """
    test_state = state.DFTimewolfState(config.Config)
    aws_logging_collector = aws_logging.AWSLogsCollector(test_state)

    query_filter = 'Username,fakename'
    start_time = '2021-01-01 00:00:00'
    end_time = '2021-01-02 00:00:00'
    aws_logging_collector.SetUp('zone', query_filter=query_filter,
        start_time=start_time, end_time=end_time)
    aws_logging_collector.Process()

    # pylint: disable=protected-access
    aws_logging_collector._log_client.LookupEvents.assert_called_with(
        qfilter=query_filter, starttime=dt.fromisoformat(start_time),
        endtime = dt.fromisoformat(end_time))


if __name__ == '__main__':
  unittest.main()
