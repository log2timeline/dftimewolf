#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the BigQuery  collector."""

import unittest
import mock
import pandas as pd

from dftimewolf.lib import state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.collectors import bigquery

from dftimewolf import config


class BigQueryCollectorTest(unittest.TestCase):
  """Tests for the BigQuery collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    bq_collector = bigquery.BigQueryCollector(test_state)
    self.assertIsNotNone(bq_collector)

  @mock.patch('google.cloud.bigquery.Client')
  def testQuery(self, mock_bq):
    """Tests that the collector calls the BQ client."""
    mock_bq().query().to_dataframe().to_json.return_value = "{'foo':1}"
    test_state = state.DFTimewolfState(config.Config)
    bq_collector = bigquery.BigQueryCollector(test_state)
    bq_collector.SetUp('test_project', 'test_query', 'test_description', False)
    bq_collector.Process()
    mock_bq().query.assert_called_with('test_query')
    mock_bq().query().to_dataframe().to_json.assert_called_once()

  @mock.patch('google.cloud.bigquery.Client')
  def testQueryPandaOutput(self, mock_bq):
    """Tests placing query results in a dataframe."""
    mock_bq().query().to_dataframe.return_value = pd.DataFrame([1], ['foo'])
    test_state = state.DFTimewolfState(config.Config)
    bq_collector = bigquery.BigQueryCollector(test_state)
    bq_collector.SetUp('test_project', 'test_query', 'test_description', True)
    bq_collector.Process()
    mock_bq().query.assert_called_with('test_query')

    conts = test_state.GetContainers(containers.DataFrame)
    self.assertEqual(len(conts), 1)

    pd.testing.assert_frame_equal(conts[0].data_frame,
                                  pd.DataFrame([1], ['foo']))


if __name__ == '__main__':
  unittest.main()
