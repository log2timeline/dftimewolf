#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Workspace logging timesketch processor."""

import unittest

from dftimewolf import config
from dftimewolf.lib import errors
from dftimewolf.lib import state
from dftimewolf.lib.collectors import gsheets
import mock


VALID_SHEET = {'range': 'Sheet1!A1:Z1000', 'majorDimension': 'ROWS', 'values': [['message', 'timestamp', 'datetime', 'timestamp_desc ', 'extra_field_1 ', 'extra_field_2'], ['A message', '1331698658276340', '2015-07-24T19:01:01+00:00', 'Write time', 'foo ', 'bar'], ['', '1331698658276340', '2016-07-24T19:01:01+00:00', 'create', 'dodo' ], ['sdsadasd', '', '', 'ddd', 'dodo', 'd']]} # pylint: disable=line-too-long
# Missing "datetime" columnd
INVALID_SHEET = {'range': 'Sheet2!A1:Y1000', 'majorDimension': 'ROWS', 'values': [['message', 'timestamp', 'timestamp_desc ', 'extra_field_1 ','extra_field_2'], ['A message', '1331698658276340', 'Write time', 'foo ', 'bar'],['', '1331698658276340', 'create', 'dodo'],['sdsadasd', '', 'ddd', 'dodo', 'd']]} # pylint: disable=line-too-long

class GoogleSheetsCollectorTest(unittest.TestCase):
  """Tests for the Google Sheets collector module ."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    collector = gsheets.GoogleSheetsCollector(test_state)
    self.assertIsNotNone(collector)

  def testValidateSpreadSheetId(self):
    """Tests that the collector validate and extract spreadsheet id."""
    test_state = state.DFTimewolfState(config.Config)
    collector = gsheets.GoogleSheetsCollector(test_state)

    with self.assertRaises(errors.DFTimewolfError) as error:
      invalid_id = 'invalid-id'
      collector._ValidateSpreadSheetId(invalid_id)

    valid_id = '1DD78vj61BEBoqpw69EdOoaxBUdDqM1GFxk5qRj7-vr4'
    self.assertEqual(
        collector._ValidateSpreadSheetId(valid_id),
        '1DD78vj61BEBoqpw69EdOoaxBUdDqM1GFxk5qRj7-vr4')

    with self.assertRaises(errors.DFTimewolfError) as error:
      invalid_id_in_url = 'https://docs.google.com/spreadsheets/d/invalid-id/edit#gid=0'
      collector._ValidateSpreadSheetId(invalid_id_in_url)

    valid_id_in_url = 'https://docs.google.com/spreadsheets/d/1DD78vj61BEBoqpw69EdOoaxBUdDqM1GFxk5qRj7-vr4/edit#gid=0'
    collector._ValidateSpreadSheetId(valid_id_in_url)
    self.assertEqual(
        collector._ValidateSpreadSheetId(valid_id_in_url),
        '1DD78vj61BEBoqpw69EdOoaxBUdDqM1GFxk5qRj7-vr4')

  @mock.patch('dftimewolf.lib.collectors.gsheets.discovery')
  def testExtractEntiresFromSheet(self, _mock_discovery):
    """Tests that the collector can extract entries from a valid sheet and
      returns None for invalid sheet if validate_columns is True. And that it
      can extract entries from both valid and invalid sheets if validate_columns
      is False.
    """
    test_state = state.DFTimewolfState(config.Config)
    collector = gsheets.GoogleSheetsCollector(test_state)

    spreadsheet_id = '1DD78vj61BEBoqpw69EdOoaxBUdDqM1GFxk5qRj7-vr4'
    sheet_title = 'Sheet1'

    service = _mock_discovery.build.return_value

    # Testing with column validation is True
    collector.SetUp(spreadsheet_id, sheet_title, True)

    service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = VALID_SHEET

    self.assertIsNotNone(collector._ExtractEntiresFromSheet(spreadsheet_id, sheet_title))

    service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = INVALID_SHEET

    self.assertIsNone(collector._ExtractEntiresFromSheet(spreadsheet_id, sheet_title))

    # Testing with column validation is False
    collector.SetUp(spreadsheet_id, sheet_title, False)

    service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = VALID_SHEET

    self.assertIsNotNone(collector._ExtractEntiresFromSheet(spreadsheet_id, sheet_title))

    service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = INVALID_SHEET

    self.assertIsNotNone(collector._ExtractEntiresFromSheet(spreadsheet_id, sheet_title))


if __name__ == '__main__':
  unittest.main()
