#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the AWS logging collector."""


import datetime
import unittest
from unittest import mock
from datetime import datetime as dt

from botocore import exceptions as boto_exceptions

from dftimewolf.lib.collectors import aws_logging
from dftimewolf.lib.containers import containers
from dftimewolf.lib import errors
from tests.lib import modules_test_base


class AWSLoggingTest(modules_test_base.ModuleTestBase):
  """Tests for the AWS logging collector."""

  def setUp(self):
    self._module: aws_logging.AWSLogsCollector
    self._InitModule(aws_logging.AWSLogsCollector)
    super().setUp()

  def testSetup(self):
    """Tests that attributes are properly set during setup."""
    self._module.SetUp(
        region='fake-region',
        profile_name='default',
        query_filter='Username,fakename',
        start_time=datetime.datetime(2021, 1, 1, 0, 0, 0),
        end_time=datetime.datetime(2021, 1, 2, 0, 0, 0))

    # pylint: disable=protected-access
    self.assertEqual(self._module._region, 'fake-region')
    self.assertEqual(self._module._profile_name, 'default')
    self.assertEqual(self._module._query_filter, 'Username,fakename')
    self.assertEqual(
        self._module._start_time,
        dt.fromisoformat('2021-01-01 00:00:00'))
    self.assertEqual(
        self._module._end_time,
        dt.fromisoformat('2021-01-02 00:00:00'))

  @mock.patch('boto3.session.Session')
  def testProcess(self, mock_boto3):
    """Tests the process method."""
    mock_session = mock.MagicMock(spec=['client'])
    mock_client = mock.MagicMock(spec=['lookup_events', 'get_caller_identity'])
    mock_client.lookup_events.return_value = {'Events': [{'log_line':1}]}
    mock_session.client.return_value = mock_client
    mock_boto3.return_value = mock_session

    self._module.SetUp(
        region='fake-region',
        query_filter='Username,fakename',
        start_time=datetime.datetime(2021, 1, 1, 0, 0, 0),
        end_time=datetime.datetime(2021, 1, 2, 0, 0, 0))
    self._ProcessModule()

    mock_session.client.assert_called_with(
        'cloudtrail', region_name='fake-region')
    mock_client.lookup_events.assert_called_with(
        LookupAttributes=[
          {
            'AttributeKey': 'Username',
            'AttributeValue': 'fakename'
          }
        ],
        StartTime=dt.fromisoformat('2021-01-01 00:00:00'),
        EndTime=dt.fromisoformat('2021-01-02 00:00:00'))

    aws_containers = self._module.GetContainers(containers.File)
    self.assertTrue(aws_containers)
    self.assertEqual(aws_containers[0].name, 'AWSLogsCollector result')

    mock_client.get_caller_identity.side_effect = (
        boto_exceptions.NoCredentialsError)
    with self.assertRaises(errors.DFTimewolfError):
      self._ProcessModule()
    mock_client.get_caller_identity.side_effect = None

    mock_client.lookup_events.side_effect = (
        boto_exceptions.ClientError({}, 'abc'))
    with self.assertRaises(errors.DFTimewolfError):
      self._ProcessModule()
    mock_client.lookup_events.side_effect = None


if __name__ == '__main__':
  unittest.main()
