#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Timesketch collector."""

import datetime
from typing import Any

import mock
import pandas as pd

from dftimewolf.lib.collectors import timesketch
from dftimewolf.lib.containers import containers
from tests.lib import modules_test_base


class TimesketchSearchEventCollectorTest(modules_test_base.ModuleTestBase):
  """Tests for the TimesketchSearchEventCollector module."""

  # For pytype
  _module: timesketch.TimesketchSearchEventCollector

  def setUp(self) -> None:
    self._InitModule(timesketch.TimesketchSearchEventCollector)
    super().setUp()

  @mock.patch("dftimewolf.lib.timesketch_utils.GetApiClient")
  def testSetupWithToken(self, mock_get_api_client: Any) -> None:
    """Tests the SetUp function with token."""
    self._module.SetUp(
      sketch_id="1",
      start_datetime=datetime.datetime(2024, 11, 11),
      end_datetime=datetime.datetime(2024, 11, 12),
      token_password="test_token",
    )
    self.assertEqual(self._module.sketch_id, 1)
    self.assertEqual(self._module.query_string, "*")
    self.assertEqual(
      self._module.start_datetime, datetime.datetime(2024, 11, 11)
    )
    self.assertEqual(self._module.end_datetime, datetime.datetime(2024, 11, 12))
    self.assertEqual(self._module.labels, [])
    self.assertEqual(self._module.output_format, "pandas")
    self.assertFalse(self._module.include_internal_columns)
    self.assertEqual(self._module.search_name, "")
    self.assertEqual(self._module.search_description, "")
    mock_get_api_client.assert_called_with(
      self._cache, token_password="test_token")

  @mock.patch("dftimewolf.lib.timesketch_utils.GetApiClient")
  def testSetupWithTicketAttributeContainer(
    self, _mock_get_api_client: Any) -> None:
    """Tests the SetUp with the sketch ID in a attribute container."""
    self._module.StoreContainer(
      containers.TicketAttribute(
        name="Timesketch URL", value="sketch/123/", type_="text"
      )
    )
    self._module.SetUp(
      start_datetime=datetime.datetime(2024, 11, 11),
      end_datetime=datetime.datetime(2024, 11, 12),
      token_password="test_token",
    )
    self.assertEqual(self._module.sketch_id, 123)

  @mock.patch("dftimewolf.lib.timesketch_utils.GetApiClient")
  @mock.patch("timesketch_api_client.client.TimesketchApi")
  def testSetupWithUsername(
    self, mock_timesketch_api: Any, _mock_get_api_client: Any
  ) -> None:
    """Tests the SetUp function with username."""
    self._module.SetUp(
      sketch_id="1",
      query_string="test",
      start_datetime=datetime.datetime(2024, 11, 11),
      end_datetime=datetime.datetime(2024, 11, 12),
      indices="1,2,3",
      labels="test,123",
      output_format="json",
      search_name="name",
      search_description="description",
      include_internal_columns=True,
      endpoint="127.0.0.1",
      username="user",
      password="pass",
    )

    self.assertEqual(self._module.sketch_id, 1)
    self.assertEqual(self._module.query_string, "test")
    self.assertEqual(
      self._module.start_datetime, datetime.datetime(2024, 11, 11)
    )
    self.assertEqual(self._module.end_datetime, datetime.datetime(2024, 11, 12))
    self.assertEqual(self._module.indices, [1, 2, 3])
    self.assertEqual(self._module.labels, ["test", "123"])
    self.assertEqual(self._module.output_format, "json")
    self.assertTrue(self._module.include_internal_columns)
    self.assertEqual(self._module.search_name, "name")
    self.assertEqual(self._module.search_description, "description")
    mock_timesketch_api.assert_called_with("127.0.0.1", "user", "pass")

  @mock.patch("dftimewolf.lib.timesketch_utils.GetApiClient")
  @mock.patch("timesketch_api_client.search")
  def testSetup(
    self,
    _mock_search: Any,
    _mock_get_api_client: Any) -> None:
    """Tests the SetUp function with token."""
    self._module.SetUp(
      sketch_id="1",
      start_datetime=datetime.datetime(2024, 11, 11),
      end_datetime=datetime.datetime(2024, 11, 12),
      token_password="test_token",
    )
    self.assertEqual(self._module.sketch_id, 1)
    self.assertEqual(self._module.query_string, "*")
    self.assertEqual(
      self._module.start_datetime, datetime.datetime(2024, 11, 11)
    )
    self.assertEqual(self._module.end_datetime, datetime.datetime(2024, 11, 12))
    self.assertEqual(self._module.labels, [])
    self.assertEqual(self._module.output_format, "pandas")
    self.assertFalse(self._module.include_internal_columns)
    self.assertEqual(self._module.search_name, "")
    self.assertEqual(self._module.search_description, "")

  @mock.patch("dftimewolf.lib.timesketch_utils.GetApiClient")
  @mock.patch.object(
    timesketch.TimesketchSearchEventCollector, "_GetSearchResults"
  )
  def testProcessPandas(
    self,
    mock_get_search_results: Any,
    _mock_get_api_client: Any) -> None:
    """Test the Process function with Pandas output."""
    mock_get_search_results.return_value = pd.DataFrame([1, 2])
    self._module.SetUp(
      sketch_id="1",
      start_datetime=datetime.datetime(2024, 11, 11),
      end_datetime=datetime.datetime(2024, 11, 12),
      token_password="test_token",
    )
    self._ProcessModule()

    state_containers = self._module.GetContainers(containers.TimesketchEvents)
    self.assertEqual(len(state_containers), 1)
    pd.testing.assert_frame_equal(
      state_containers[0].data_frame, pd.DataFrame([1, 2])
    )

  @mock.patch("dftimewolf.lib.timesketch_utils.GetApiClient")
  @mock.patch.object(
    timesketch.TimesketchSearchEventCollector, "_GetSearchResults"
  )
  def testProcessNoSketchId(
    self,
    _mock_get_search_results: Any,
    mock_get_api_client: Any
  ) -> None:
    """Test the Process function with no sketch ID."""
    with (mock.patch.object(self._cache, 'GetFromCache', return_value=None)
          as mock_getfromcache):
      self._module.SetUp(
        sketch_id=None,
        start_datetime=datetime.datetime(2024, 11, 11),
        end_datetime=datetime.datetime(2024, 11, 12),
        token_password="test_token",
      )

    # Simulating another module adding a TicketAttribute container
    # netween SetUp() and Process()

      self._module.StoreContainer(
        containers.TicketAttribute(
          name="Timesketch URL", value="sketch/123/", type_="text"
        )
      )

      self._ProcessModule()
      mock_getfromcache.assert_has_calls(
        [mock.call("timesketch_sketch"), mock.call("timesketch_sketch")]
      )
      mock_get_api_client.return_value.get_sketch.assert_called_with(123)

  @mock.patch("dftimewolf.lib.timesketch_utils.GetApiClient")
  @mock.patch.object(
    timesketch.TimesketchSearchEventCollector, "_GetSearchResults"
  )
  def testParameterPrecedenceSetup(
    self, _mock_get_search_results: Any, mock_get_api_client: Any
  ) -> None:
    """Tests that the ID passed in SetUp takes precedence over cached
    sketches and attribute containers."""

    self._module.GetFromCache = mock.MagicMock(return_value=None)

    self._module.StoreContainer(
      containers.TicketAttribute(
        name="Timesketch URL", value="sketch/123/", type_="text"
      )
    )

    mock_cached_sketch = mock.MagicMock()
    mock_cached_sketch.id = 666
    self._module.AddToCache("timesketch_sketch", mock_cached_sketch)

    self._module.SetUp(
      sketch_id="999",
      start_datetime=datetime.datetime(2024, 11, 11),
      end_datetime=datetime.datetime(2024, 11, 12),
      token_password="test_token",
    )

    # Simulating another module adding a TicketAttribute container
    # netween SetUp() and Process()

    self._ProcessModule()
    self._module.GetFromCache.assert_not_called()
    self.assertEqual(self._module.sketch_id, 999)
    mock_get_api_client.return_value.get_sketch.assert_called_once_with(999)

  @mock.patch("dftimewolf.lib.timesketch_utils.GetApiClient")
  @mock.patch.object(
    timesketch.TimesketchSearchEventCollector, "_GetSearchResults"
  )
  def testParameterPrecedenceCache(
    self, _mock_get_search_results: Any, mock_get_api_client: Any
  ) -> None:
    """Test that a sketch found in the cache takes precedence over one specified
    in attribute containers."""

    self._module.StoreContainer(
      containers.TicketAttribute(
        name="Timesketch URL", value="sketch/123/", type_="text"
      )
    )

    mock_sketch = mock.MagicMock()
    mock_sketch.id = 666
    self._module.AddToCache("timesketch_sketch", mock_sketch)

    self._module.SetUp(
      sketch_id=None,
      start_datetime=datetime.datetime(2024, 11, 11),
      end_datetime=datetime.datetime(2024, 11, 12),
      token_password="test_token",
    )

    # Simulating another module adding a TicketAttribute container
    # netween SetUp() and Process()

    self._ProcessModule()
    self.assertEqual(self._module.sketch_id, 666)
    mock_get_api_client.return_value.get_sketch.assert_not_called()

  @mock.patch("dftimewolf.lib.timesketch_utils.GetApiClient")
  @mock.patch.object(
    timesketch.TimesketchSearchEventCollector, "_GetSearchResults"
  )
  def testStoreAggregationContainer(
    self, mock_get_search_results: Any, _mock_get_api_client: Any
  ) -> None:
    """Tests the _StoreDataTypesAggregationContainer function."""
    # Mocking the search results
    mock_get_search_results.return_value = pd.DataFrame(
      {"data_type": ["type1", "type2", "type1", "type3", "type2"]}
    )

    self._module.SetUp(
      sketch_id="1",
      start_datetime=datetime.datetime(2024, 11, 11),
      end_datetime=datetime.datetime(2024, 11, 12),
      token_password="test_token",
    )

    # Running the module process
    self._ProcessModule()

    # Checking if the aggregation container was stored correctly
    containers_list = self._module.GetContainers(
      containers.TimesketchAggregation
    )
    self.assertEqual(len(containers_list), 1)
    aggregation_container = containers_list[0]

    self.assertEqual(aggregation_container.name, "data_types")
    self.assertEqual(aggregation_container.key, "data_type")
    self.assertEqual(
      aggregation_container.description, "Data types in the search results"
    )
