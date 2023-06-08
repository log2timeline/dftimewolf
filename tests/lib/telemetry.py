#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the Telemetry modules."""

import unittest
import mock

try:
  from google.cloud import spanner
  HAS_SPANNER = True
except ImportError:
  HAS_SPANNER = False

from dftimewolf.lib import telemetry


class BaseTelemetryTest(unittest.TestCase):
  """Tests for the DFTimewolfState class."""

  def tearDown(self):
    """Delete singleton attributes."""
    if hasattr(telemetry.BaseTelemetry, 'instance'):
      delattr(telemetry.BaseTelemetry, 'instance')
    if hasattr(telemetry.GoogleCloudSpannerTelemetry, 'instance'):
      delattr(telemetry.GoogleCloudSpannerTelemetry, 'instance')

  @mock.patch('uuid.uuid4', return_value='test_uuid')
  def testInit(self, unused_mock_uuid):
    """Tests that the BaseTelemetry object is properly initialized."""
    telemetry1 = telemetry.BaseTelemetry()
    self.assertEqual(telemetry1.uuid, 'test_uuid')
    self.assertEqual(telemetry1.entries, [])

  def testLogTelemetry(self):
    """Tests that LogTelemetry logs the correct data."""
    telemetry1 = telemetry.BaseTelemetry()
    telemetry1.LogTelemetry(
      'test_key', 'test_value', 'random_module', 'random_recipe')
    self.assertEqual(len(telemetry1.entries), 1)
    self.assertEqual(
        telemetry1.entries[0],
        '\ttest_key: \ttest_value (random_module in random_recipe)')

  # patch UUID to return a constant value
  @mock.patch('uuid.uuid4', return_value='test_uuid')
  def testFormatTelemetry(self, unused_mock_uuid):
    """Tests that the resulting Telemetry is properly formatted."""
    telemetry1 = telemetry.BaseTelemetry()
    telemetry1.LogTelemetry(
      'test_key', 'test_value', 'random_module', 'random_recipe')
    result = telemetry1.FormatTelemetry()
    self.assertEqual(
        result,
        ('Telemetry information for: test_uuid\n\ttest_key:'
         ' \ttest_value (random_module in random_recipe)')
    )

@unittest.skipIf(not HAS_SPANNER, 'Missing google.cloud.spanner dependency.')
class GoogleCloudSpannerTelemetryTest(unittest.TestCase):
  """Tests for the DFTimewolfState class."""

  def setUp(self):
    """Patch the Google Cloud Spanner Client class."""
    self.patcher = mock.patch('google.cloud.spanner.Client')
    self.mock_spanner_client = self.patcher.start()

  def tearDown(self):
    """Delete singleton attributes, stop patching."""
    if hasattr(telemetry.BaseTelemetry, 'instance'):
      delattr(telemetry.BaseTelemetry, 'instance')
    if hasattr(telemetry.GoogleCloudSpannerTelemetry, 'instance'):
      delattr(telemetry.GoogleCloudSpannerTelemetry, 'instance')
    self.patcher.stop()

  def testSingleton(self):
    """Tests that the singleton property of the Telemetry object holds."""
    telemetry1 = telemetry.GoogleCloudSpannerTelemetry(
        project_name='test_project',
        instance_name='test_instance',
        database_name='test_database')
    telemetry2 = telemetry.GoogleCloudSpannerTelemetry(
        project_name='foo', instance_name='bar', database_name='bas')

    self.assertEqual(id(telemetry1), id(telemetry2))
    self.assertEqual(id(telemetry1.database), id(telemetry2.database))

  def testInit(self):
    """Tests that the GoogleCloudSpannerTelemetry object is properly
    initialized."""
    telemetry1 = telemetry.GoogleCloudSpannerTelemetry(
        project_name='test_project',
        instance_name='test_instance',
        database_name='test_database')
    self.assertIsNotNone(telemetry1.uuid)
    self.assertIsNotNone(telemetry1.database)
    self.mock_spanner_client.assert_called_with(project='test_project')
    instance = self.mock_spanner_client.return_value.instance
    instance.assert_called_with('test_instance')
    database = instance.return_value.database
    database.assert_called_with('test_database')

  # patch UUID to return a constant value
  @mock.patch('uuid.uuid4', return_value='test_uuid')
  def testFormatTelemetrySelectStatement(self, unused_mock_uuid):
    """Tests that the Spanner SELECT statement is crafted correctly."""
    telemetry1 = telemetry.GoogleCloudSpannerTelemetry(
        project_name='test_project',
        instance_name='test_instance',
        database_name='test_database')

    entries = []
    transaction = mock.Mock()
    transaction.execute_sql.return_value = [[
        'row0_data', 'row1_data', 'row2_data', 'row3_data', 'row4_data'
    ]]
    # pylint: disable=protected-access
    telemetry1._GetAllWorkflowTelemetryTransaction(transaction, entries)
    transaction.execute_sql.assert_called_with(
        'SELECT * from Telemetry WHERE workflow_uuid = @uuid ORDER BY time ASC',
        params={'uuid': 'test_uuid'},
        param_types={'uuid': spanner.param_types.STRING})
    self.assertEqual(entries[0], 'Telemetry information for: test_uuid')
    self.assertEqual(
        entries[1], '\trow1_data:\t\trow2_data - row3_data: row4_data')

  @mock.patch('uuid.uuid4', return_value='test_uuid')
  def testLogTelemetryInsert(self, unused_mock_uuid):
    """Tests that the correct insert call is made when adding telemetry."""
    telemetry1 = telemetry.GoogleCloudSpannerTelemetry(
        project_name='test_project',
        instance_name='test_instance',
        database_name='test_database')
    mock_transaction = mock.Mock()
    fake_telemetry = {
        'test_key1': 'test_value1',
        'test_key4': 'test_value4',
        'test_key2': 'test_value2',
        'test_key3': 'test_value3',
    }
    # pylint: disable=protected-access
    telemetry1._LogTelemetryTransaction(mock_transaction, fake_telemetry)
    mock_transaction.insert.assert_called_once()
    args = mock_transaction.insert.call_args
    self.assertEqual(args.kwargs['table'], 'Telemetry')
    # Here we're testing that columns are mapped to their correct value by
    # comparing the last character of the column name and the last character
    # of the value.
    for i in range(0, 4):
      column = args.kwargs['columns'][i]
      value = args.kwargs['values'][0][i]
      self.assertEqual(column[-1], value[-1])

  @mock.patch('uuid.uuid4', return_value='test_uuid')
  def testLogTelemetryRunInTransaction(self, unused_mock_uuid):
    """Tests that the data to be inserted is properly formed."""
    telemetry1 = telemetry.GoogleCloudSpannerTelemetry(
        project_name='test_project',
        instance_name='test_instance',
        database_name='test_database')
    telemetry1.LogTelemetry(
      'test_key', 'test_value', 'random_module', 'random_recipe')
    instance = self.mock_spanner_client.return_value.instance.return_value
    database = instance.database.return_value
    database.run_in_transaction.assert_called_with(
        telemetry1._LogTelemetryTransaction,  # pylint: disable=protected-access
        {
            'workflow_uuid': 'test_uuid',
            'time': mock.ANY,
            'recipe': 'random_recipe',
            'source_module': 'random_module',
            'key': 'test_key',
            'value': 'test_value'
        })


if __name__ == '__main__':
  unittest.main()
