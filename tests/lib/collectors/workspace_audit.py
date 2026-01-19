#!/usr/bin/env python
"""Tests the Workspace audit collector."""

from unittest import mock
import unittest
import datetime

from dftimewolf.lib import errors
from dftimewolf.lib import state
from dftimewolf.lib.collectors import workspace_audit


class WorkspaceAuditCollectorTest(unittest.TestCase):
  """Tests for the Workspace audit collector."""

  def setUp(self):
    self.ws_collector = workspace_audit.WorkspaceAuditCollector(
        name='',
        cache_=mock.MagicMock(),
        container_manager_=mock.MagicMock(),
        telemetry_=mock.MagicMock(),
        publish_message_callback=mock.MagicMock())

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
        # This is > 6mo before 2023-01-01
        start_time=datetime.datetime(
            2022, 1,  1, 0, 0, 0, tzinfo=datetime.timezone.utc),
        end_time=datetime.datetime
        (2023, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
      )
    self.assertEqual(
      error.exception.message,
      'Maximum gWorkspace retention is 6 months. Please choose a more recent '
      'start date (Earliest: 2022-07-05T00:00:00Z).')





if __name__ == '__main__':
  unittest.main()
