#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Timesketch collector."""
import datetime
import unittest

import mock
import pandas as pd

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.containers import containers
from dftimewolf.lib.collectors import timesketch

class TimesketchSearchEventCollectorTest(unittest.TestCase):
  """Tests for the TimesketchSearchEventCollector module."""

  @mock.patch('dftimewolf.lib.timesketch_utils.GetApiClient')
  def testSetupWithToken(self, mock_get_api_client):
    """Tests the SetUp function with token."""
    test_state = state.DFTimewolfState(config.Config)
    timesketch_collector = timesketch.TimesketchSearchEventCollector(
        test_state)
    timesketch_collector.SetUp(
        sketch_id='1',
        start_datetime=datetime.datetime(2024, 11, 11),
        end_datetime=datetime.datetime(2024, 11, 12),
        token_password='test_token')
    self.assertEqual(timesketch_collector.sketch_id, 1)
    self.assertEqual(timesketch_collector.query_string, '*')
    self.assertEqual(
        timesketch_collector.start_datetime, datetime.datetime(2024, 11, 11))
    self.assertEqual(
        timesketch_collector.end_datetime, datetime.datetime(2024, 11, 12))
    self.assertEqual(timesketch_collector.labels, [])
    self.assertEqual(timesketch_collector.output_format, 'pandas')
    self.assertFalse(timesketch_collector.include_internal_columns)
    self.assertEqual(timesketch_collector.search_name, '')
    self.assertEqual(timesketch_collector.search_description, '')
    mock_get_api_client.assert_called_with(
        test_state, token_password='test_token')

  @mock.patch('dftimewolf.lib.timesketch_utils.GetApiClient')
  @mock.patch('timesketch_api_client.client.TimesketchApi')
  def testSetupWithUsername(self, mock_timesketch_api, _mock_get_api_client):
    """Tests the SetUp function with username."""
    test_state = state.DFTimewolfState(config.Config)
    timesketch_collector = timesketch.TimesketchSearchEventCollector(test_state)
    timesketch_collector.SetUp(
        sketch_id='1',
        query_string='test',
        start_datetime=datetime.datetime(2024, 11, 11),
        end_datetime=datetime.datetime(2024, 11, 12),
        indices='1,2,3',
        labels='test,123',
        output_format='json',
        search_name='name',
        search_description='description',
        include_internal_columns=True,
        endpoint='127.0.0.1',
        username='user',
        password='pass')

    self.assertEqual(timesketch_collector.sketch_id, 1)
    self.assertEqual(timesketch_collector.query_string, 'test')
    self.assertEqual(
        timesketch_collector.start_datetime, datetime.datetime(2024, 11, 11))
    self.assertEqual(
        timesketch_collector.end_datetime, datetime.datetime(2024, 11, 12))
    self.assertEqual(timesketch_collector.indices, [1, 2, 3])
    self.assertEqual(timesketch_collector.labels, ['test', '123'])
    self.assertEqual(timesketch_collector.output_format, 'json')
    self.assertTrue(timesketch_collector.include_internal_columns)
    self.assertEqual(timesketch_collector.search_name, 'name')
    self.assertEqual(timesketch_collector.search_description, 'description')
    mock_timesketch_api.assert_called_with('127.0.0.1', 'user', 'pass')

  @mock.patch('dftimewolf.lib.timesketch_utils.GetApiClient')
  @mock.patch('timesketch_api_client.search')
  def testSetup(self, _mock_search, _mock_get_api_client):
    """Tests the SetUp function with token."""
    test_state = state.DFTimewolfState(config.Config)
    timesketch_collector = timesketch.TimesketchSearchEventCollector(
        test_state)
    timesketch_collector.SetUp(
        sketch_id='1',
        start_datetime=datetime.datetime(2024, 11, 11),
        end_datetime=datetime.datetime(2024, 11, 12),
        token_password='test_token')
    self.assertEqual(timesketch_collector.sketch_id, 1)
    self.assertEqual(timesketch_collector.query_string, '*')
    self.assertEqual(
        timesketch_collector.start_datetime, datetime.datetime(2024, 11, 11))
    self.assertEqual(
        timesketch_collector.end_datetime, datetime.datetime(2024, 11, 12))
    self.assertEqual(timesketch_collector.labels, [])
    self.assertEqual(timesketch_collector.output_format, 'pandas')
    self.assertFalse(timesketch_collector.include_internal_columns)
    self.assertEqual(timesketch_collector.search_name, '')
    self.assertEqual(timesketch_collector.search_description, '')

  @mock.patch('dftimewolf.lib.timesketch_utils.GetApiClient')
  @mock.patch.object(
      timesketch.TimesketchSearchEventCollector,
      '_GetSearchResults')
  def testProcessPandas(self, mock_get_search_results, _mock_get_api_client):
    """Test the Process function with Pandas output."""
    mock_get_search_results.return_value = pd.DataFrame([1, 2])
    test_state = state.DFTimewolfState(config.Config)
    timesketch_collector = timesketch.TimesketchSearchEventCollector(test_state)
    timesketch_collector.SetUp(
        sketch_id='1',
        start_datetime=datetime.datetime(2024, 11, 11),
        end_datetime=datetime.datetime(2024, 11, 12),
        token_password='test_token')
    timesketch_collector.Process()

    state_containers = test_state.GetContainers(containers.DataFrame)
    self.assertEqual(len(state_containers), 1)
    pd.testing.assert_frame_equal(
        state_containers[0].data_frame, pd.DataFrame([1, 2]))


if __name__ == '__main__':
  unittest.main()
