#!/usr/bin/env python
"""Tests the Workspace audit collector."""

from unittest import mock
import unittest
import datetime

from dftimewolf.lib import errors
from dftimewolf.lib import state
from dftimewolf.lib.collectors import workspace_audit
from dftimewolf.lib.containers import containers

from dftimewolf import config


class WorkspaceAuditCollectorTest(unittest.TestCase):
  """Tests for the Workspace audit collector."""

  def setUp(self):
    test_state = state.DFTimewolfState(config.Config)
    self.ws_collector = workspace_audit.WorkspaceAuditCollector(test_state, name='test')

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self.ws_collector)

  @mock.patch.object(workspace_audit.WorkspaceAuditCollector, '_GetCredentials')
  @mock.patch.object(workspace_audit, 'datetime')
  def testSetUpDates(self, mock_datetime, unused_mock_get_credentials):
    """Tests that an exception is raised if the start time is too old."""

    # freeze time to 2023-01-01
    mock_datetime.datetime.now.return_value = datetime.datetime(
      2023, 1, 1, tzinfo=datetime.timezone.utc)
    mock_datetime.datetime.fromisoformat = datetime.datetime.fromisoformat
    mock_datetime.timedelta = datetime.timedelta

    # Assert that set up with old date fails
    with self.assertRaises(errors.DFTimewolfError) as error:
      self.ws_collector.SetUp(
        application_name='test',
        filter_expression='test',
        user_key='test',
        start_time='2022-01-01T00:00:00Z',  # This is longer than 6mo before 2023-01-01
        end_time='2023-01-01T00:00:00Z',
      )
      self.assertEqual(
        error.exception.message,
        'Maximum gWorkspace retention is 6 months. Please choose a more recent '
        'start date.')

    # Assert that setup with recent date works as expected.
    self.ws_collector.SetUp(
        application_name='test',
        filter_expression='test',
        user_key='test',
        start_time='2022-12-01T00:00:00Z',  # This is 1mo before 2023-01-01
        end_time='2023-01-01T00:00:00Z',
      )
    # pylint: disable=protected-access
    self.assertEqual(self.ws_collector._start_time, '2022-12-01T00:00:00Z')
    self.assertEqual(self.ws_collector._end_time, '2023-01-01T00:00:00Z')



if __name__ == '__main__':
  unittest.main()
