#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Turbinia processor."""

import unittest
import json
import os
import mock

from dftimewolf.lib.processors import turbinia_base_api

YARA_RULE = """rule dummy { condition: false }"""
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
TASK_ID = "3a5759372b594c0bb2a81cda805ca9a0"
# pylint: disable=line-too-long
TEST_TASK_PATH = "/mnt/turbiniavolume/output/3a5759372b594c0bb2a81cda805ca9a0/1680565159-c4e9abd577db475484b2ded34a011b96-PlasoParserTask/c4e9abd577db475484b2ded34a011b96.plaso"

class TurbiniaBaseTest(unittest.TestCase):
  """Tests for the Turbinia processor."""
  def setUp(self):
    """Tests that the processor can be initialized."""
    self.logger = mock.MagicMock()
    self.turbinia_processor = turbinia_base_api.TurbiniaAPIProcessorBase(
        self.logger
    )
    file_path = os.path.join(
        CURRENT_DIR, "test_data", "turbinia_request_status.json")
    self._request_status = json.load(open(file_path))

  # pylint: disable=line-too-long
  @mock.patch(
      "turbinia_api_lib.api.turbinia_configuration_api.TurbiniaConfigurationApi.read_config"
  )
  def testTurbiniaSetup(self, _mock_read_config):
    """Tests the TurbiniaSetup method."""
    _mock_read_config.return_value = {"OUTPUT_DIR": "/tmp"}
    self.turbinia_processor.TurbiniaSetUp(
        project="turbinia-project",
        turbinia_auth=False,
        turbinia_recipe=None,
        turbinia_zone="us-central1f",
        turbinia_api="http://localhost:8001",
        incident_id="123456789",
        sketch_id="12345",
    )
    self.assertEqual(self.turbinia_processor.project, "turbinia-project")
    self.assertEqual(self.turbinia_processor.turbinia_zone, "us-central1f")
    self.assertEqual(self.turbinia_processor.turbinia_api, "http://localhost:8001")
    self.assertEqual(self.turbinia_processor.incident_id, "123456789")
    self.assertEqual(self.turbinia_processor.sketch_id, "12345")
    self.assertEqual(self.turbinia_processor.output_path, "/tmp")
    self.assertEqual(self.turbinia_processor.turbinia_recipe, None)

  # pylint: disable=line-too-long
  @mock.patch(
      "turbinia_api_lib.api.turbinia_requests_api.TurbiniaRequestsApi.create_request"
  )
  def testTurbiniaStart(self, mock_create_request):
    """Tests the TurbiniaStart method."""
    mock_create_request.return_value = {
        "request_id": "41483253079448e59685d88f37ab91f7"
    }
    evidence = {
        "type": "GoogleCloudDisk",
        "disk_name": "disk-1",
        "project": "project-1",
        "zone": "us-central1-f",
    }
    request_id = self.turbinia_processor.TurbiniaStart(
        evidence=evidence, yara_rules=YARA_RULE
    )
    self.assertEqual(request_id, "41483253079448e59685d88f37ab91f7")

  # pylint: disable=line-too-long
  @mock.patch(
      "turbinia_api_lib.api.turbinia_requests_api.TurbiniaRequestsApi.get_request_status"
  )
  @mock.patch("time.sleep")
  def testTurbiniaWait(self, mock_get_request_status, _):
    """Tests the TurbiniaWait method."""
    mock_get_request_status = mock.MagicMock()
    mock_get_request_status.return_value = self._request_status
    for task, path in self.turbinia_processor.TurbiniaWait(TASK_ID):
      # Check that the task and path are correct for a PlasoParserTask
      if task["id"] == TASK_ID:
        self.assertEqual(path, TEST_TASK_PATH)
      break

  def testIsInterestingPath(self):
    """Tests the _isInterestingPath method in TurbiniaAPIProcessorBase."""
    self.assertTrue(self.turbinia_processor._isInterestingPath(TEST_TASK_PATH))

  @mock.patch('tempfile.mkdtemp')
  def testExtractPath(self, mock_tempdir):
    """Tests the _ExtractFiles method in TurbiniaAPIProcessorBase."""
    mock_tempdir.return_value = '/tmp'
    file_path = os.path.join(
        CURRENT_DIR, "test_data", "c4e9abd577db475484b2ded34a011b96.tgz")
    expected_local_path = f"/tmp{TEST_TASK_PATH}"
    local_path = self.turbinia_processor._ExtractFiles(file_path, TEST_TASK_PATH)
    self.assertEqual(local_path, expected_local_path)

if __name__ == "__main__":
  unittest.main()
