#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the BigQuery collector."""

import unittest
import mock
import pandas as pd

from dftimewolf.lib.containers import containers
from dftimewolf.lib.collectors import bigquery
from tests.lib import modules_test_base


class BigQueryCollectorTest(modules_test_base.ModuleTestBase):
  """Tests for the BigQuery collector."""

  def setUp(self):
    self._InitModule(bigquery.BigQueryCollector)
    super().setUp()

  @mock.patch('google.cloud.bigquery.Client')
  def testQuery(self, mock_bq):
    """Tests that the collector calls the BQ client."""
    mock_bq().query().to_dataframe().to_json.return_value = "{'foo':1}"
    self._module.SetUp('test_project', 'test_query', 'test_description', False)
    self._ProcessModule()

    mock_bq().query.assert_called_with('test_query')
    mock_bq().query().to_dataframe().to_json.assert_called_once()

    conts = self._module.GetContainers(containers.File)
    self.assertEqual(len(conts), 1)

    conts = self._module.GetContainers(containers.DataFrame)
    self.assertEqual(len(conts), 0)

  @mock.patch('google.cloud.bigquery.Client')
  def testQueryFromState(self, mock_bq):
    """Tests that the query runs when it's passed in via the state."""
    mock_bq().query().to_dataframe().to_json.return_value = "{'foo':1}"
    cont_in = containers.BigQueryQuery('test_query', 'test_description', True)
    cont_in.SetMetadata('input_metadata_key', 'input_metadata_value')
    self._module.StoreContainer(cont_in)
    self._module.SetUp('test_project', '', '', False)
    self._ProcessModule()

    mock_bq().query.assert_called_with('test_query')

    conts = self._module.GetContainers(containers.DataFrame)
    self.assertEqual(len(conts), 1)
    self.assertEqual(conts[0].metadata.get('input_metadata_key'),
                     'input_metadata_value')

  @mock.patch('google.cloud.bigquery.Client')
  def testQueryPandaOutput(self, mock_bq):
    """Tests placing query results in a dataframe."""
    mock_bq().query().to_dataframe.return_value = pd.DataFrame([1], ['foo'])
    self._module.SetUp('test_project', 'test_query', 'test_description', True)
    self._ProcessModule()

    mock_bq().query.assert_called_with('test_query')

    conts = self._module.GetContainers(containers.DataFrame)
    self.assertEqual(len(conts), 1)

    pd.testing.assert_frame_equal(conts[0].data_frame,
                                  pd.DataFrame([1], ['foo']))

    conts = self._module.GetContainers(containers.File)
    self.assertEqual(len(conts), 0)


if __name__ == '__main__':
  unittest.main()
