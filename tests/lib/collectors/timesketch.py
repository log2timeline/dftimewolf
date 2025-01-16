#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Timesketch collector."""
import datetime
import unittest

import mock
import pandas as pd

from dftimewolf.lib.containers import containers
from dftimewolf.lib.collectors import timesketch
from tests.lib import modules_test_base


class TimesketchSearchEventCollectorTest(modules_test_base.ModuleTestBase):
  """Tests for the TimesketchSearchEventCollector module."""

  def setUp(self):
    self._InitModule(timesketch.TimesketchSearchEventCollector)
    super().setUp()

  @mock.patch('dftimewolf.lib.timesketch_utils.GetApiClient')
  def testSetupWithToken(self, mock_get_api_client):
    """Tests the SetUp function with token."""
    self._module.SetUp(
        sketch_id='1',
        start_datetime=datetime.datetime(2024, 11, 11),
        end_datetime=datetime.datetime(2024, 11, 12),
        token_password='test_token')
    self.assertEqual(self._module.sketch_id, 1)
    self.assertEqual(self._module.query_string, '*')
    self.assertEqual(
        self._module.start_datetime, datetime.datetime(2024, 11, 11))
    self.assertEqual(
        self._module.end_datetime, datetime.datetime(2024, 11, 12))
    self.assertEqual(self._module.labels, [])
    self.assertEqual(self._module.output_format, 'pandas')
    self.assertFalse(self._module.include_internal_columns)
    self.assertEqual(self._module.search_name, '')
    self.assertEqual(self._module.search_description, '')
    mock_get_api_client.assert_called_with(
        self._test_state, token_password='test_token')

  @mock.patch('dftimewolf.lib.timesketch_utils.GetApiClient')
  def testSetupWithTicketAttributeContainer(self, _mock_get_api_client):
    """Tests the SetUp with the sketch ID in a attribute container."""
    self._module.StoreContainer(containers.TicketAttribute(
        name='Timesketch URL', value='sketch/123/', type_='text'))
    self._module.SetUp(
        start_datetime=datetime.datetime(2024, 11, 11),
        end_datetime=datetime.datetime(2024, 11, 12),
        token_password='test_token')
    self.assertEqual(self._module.sketch_id, 123)

  @mock.patch('dftimewolf.lib.timesketch_utils.GetApiClient')
  @mock.patch('timesketch_api_client.client.TimesketchApi')
  def testSetupWithUsername(self, mock_timesketch_api, _mock_get_api_client):
    """Tests the SetUp function with username."""
    self._module.SetUp(
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

    self.assertEqual(self._module.sketch_id, 1)
    self.assertEqual(self._module.query_string, 'test')
    self.assertEqual(
        self._module.start_datetime, datetime.datetime(2024, 11, 11))
    self.assertEqual(
        self._module.end_datetime, datetime.datetime(2024, 11, 12))
    self.assertEqual(self._module.indices, [1, 2, 3])
    self.assertEqual(self._module.labels, ['test', '123'])
    self.assertEqual(self._module.output_format, 'json')
    self.assertTrue(self._module.include_internal_columns)
    self.assertEqual(self._module.search_name, 'name')
    self.assertEqual(self._module.search_description, 'description')
    mock_timesketch_api.assert_called_with('127.0.0.1', 'user', 'pass')

  @mock.patch('dftimewolf.lib.timesketch_utils.GetApiClient')
  @mock.patch('timesketch_api_client.search')
  def testSetup(self, _mock_search, _mock_get_api_client):
    """Tests the SetUp function with token."""
    self._module.SetUp(
        sketch_id='1',
        start_datetime=datetime.datetime(2024, 11, 11),
        end_datetime=datetime.datetime(2024, 11, 12),
        token_password='test_token')
    self.assertEqual(self._module.sketch_id, 1)
    self.assertEqual(self._module.query_string, '*')
    self.assertEqual(
        self._module.start_datetime, datetime.datetime(2024, 11, 11))
    self.assertEqual(
        self._module.end_datetime, datetime.datetime(2024, 11, 12))
    self.assertEqual(self._module.labels, [])
    self.assertEqual(self._module.output_format, 'pandas')
    self.assertFalse(self._module.include_internal_columns)
    self.assertEqual(self._module.search_name, '')
    self.assertEqual(self._module.search_description, '')

  @mock.patch('dftimewolf.lib.timesketch_utils.GetApiClient')
  @mock.patch.object(
      timesketch.TimesketchSearchEventCollector,
      '_GetSearchResults')
  def testProcessPandas(self, mock_get_search_results, _mock_get_api_client):
    """Test the Process function with Pandas output."""
    mock_get_search_results.return_value = pd.DataFrame([1, 2])
    self._module.SetUp(
        sketch_id='1',
        start_datetime=datetime.datetime(2024, 11, 11),
        end_datetime=datetime.datetime(2024, 11, 12),
        token_password='test_token')
    self._ProcessModule()

    state_containers = self._module.GetContainers(containers.TimesketchEvents)
    self.assertEqual(len(state_containers), 1)
    pd.testing.assert_frame_equal(
        state_containers[0].data_frame, pd.DataFrame([1, 2]))


if __name__ == '__main__':
  unittest.main()
