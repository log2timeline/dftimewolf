#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Workspace logging timesketch processor."""

import unittest
import mock

from dftimewolf.lib import errors
from dftimewolf.lib.collectors import gsheets

# pylint: disable=line-too-long
VALID_SHEET = {'range': 'Sheet1!A1:Z1000', 'majorDimension': 'ROWS', 'values': [
    ['message', 'timestamp', 'datetime', 'timestamp_desc ', 'extra_field_1 ', 'extra_field_2'],
    ['A message', '1331698658276340', '2015-07-24T19:01:01+00:00', 'Write time', 'foo ', 'bar'],
    ['', '1331698658276340', '2016-07-24T19:01:01+00:00', 'creation time', 'foo', ''],
    ['A message', '', '', 'modified time', 'foo', 'bar']]}
# Missing "datetime" columnd
INVALID_SHEET = {'range': 'Sheet2!A1:Y1000', 'majorDimension': 'ROWS', 'values': [
    ['message', 'timestamp', 'timestamp_desc ', 'extra_field_1 ', 'extra_field_2'],
    ['A message', '1331698658276340', 'Write time', 'foo ', 'bar'],
    ['', '1331698658276340', 'creation time', 'foo', ''],
    ['A message', '', 'modified time', 'foo', 'bar']]}
# pylint: enable=line-too-long


class GoogleSheetsCollectorTest(unittest.TestCase):
  """Tests for the Google Sheets collector module ."""

  def setUp(self):
    super().setUp()

    self._collector = gsheets.GoogleSheetsCollector(
        name='',
        cache_=mock.MagicMock(),
        container_manager_=mock.MagicMock(),
        telemetry_=mock.MagicMock(),
        publish_message_callback=mock.MagicMock())

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self._collector)

  # pylint: disable=protected-access
  def testValidateSpreadSheetId(self):
    """Tests that the collector validate and extract spreadsheet id."""
    with self.assertRaises(errors.DFTimewolfError):
      invalid_id = 'invalid-id'
      self._collector._ValidateSpreadSheetId(invalid_id)

    valid_id = '1DD78vj61BEBoqpw69EdOoaxBUdDqM1GFxk5qRj7-vr4'
    self.assertEqual(
        self._collector._ValidateSpreadSheetId(valid_id),
        '1DD78vj61BEBoqpw69EdOoaxBUdDqM1GFxk5qRj7-vr4')

    with self.assertRaises(errors.DFTimewolfError):
      invalid_id_in_url = 'https://docs.google.com/spreadsheets/d/invalid-id/edit#gid=0' # pylint: disable=line-too-long
      self._collector._ValidateSpreadSheetId(invalid_id_in_url)

    valid_id_in_url = 'https://docs.google.com/spreadsheets/d/1DD78vj61BEBoqpw69EdOoaxBUdDqM1GFxk5qRj7-vr4/edit#gid=0' # pylint: disable=line-too-long
    self._collector._ValidateSpreadSheetId(valid_id_in_url)
    self.assertEqual(
        self._collector._ValidateSpreadSheetId(valid_id_in_url),
        '1DD78vj61BEBoqpw69EdOoaxBUdDqM1GFxk5qRj7-vr4')

  # pylint: disable=invalid-name
  @mock.patch('os.path.exists')
  @mock.patch('dftimewolf.lib.collectors.gsheets.Credentials')
  @mock.patch('dftimewolf.lib.collectors.gsheets.discovery')
  def testExtractEntriesFromSheet(self, _mock_discovery, _mock_credentials,
                                  _mock_exists):
    """Test _ExtractEntriesFromSheet() function."""
    spreadsheet_id = '1DD78vj61BEBoqpw69EdOoaxBUdDqM1GFxk5qRj7-vr4'
    sheet_title = 'Sheet1'

    # Return true so the tests assumes the client secret file exist
    _mock_exists.return_value = True
    # Return empty string for calles to check for user authorization with Google
    # Sheet API
    _mock_credentials.from_authorized_user_file().return_value = ''

    mock_spreadsheet_call = _mock_discovery.build.return_value.spreadsheets.return_value.values.return_value.get.return_value.execute # pylint: disable=line-too-long

    # Testing with column validation is True
    self._collector.SetUp(spreadsheet_id, [sheet_title], True)
    mock_spreadsheet_call.return_value = VALID_SHEET
    self.assertIsNotNone(
        self._collector._ExtractEntriesFromSheet(spreadsheet_id, sheet_title))
    mock_spreadsheet_call.return_value = INVALID_SHEET
    self.assertIsNone(
        self._collector._ExtractEntriesFromSheet(spreadsheet_id, sheet_title))

    # Testing with column validation is False
    self._collector.SetUp(spreadsheet_id, [sheet_title], False)
    mock_spreadsheet_call.return_value = VALID_SHEET
    self.assertIsNotNone(
        self._collector._ExtractEntriesFromSheet(spreadsheet_id, sheet_title))
    mock_spreadsheet_call.return_value = INVALID_SHEET
    self.assertIsNotNone(
        self._collector._ExtractEntriesFromSheet(spreadsheet_id, sheet_title))


if __name__ == '__main__':
  unittest.main()
