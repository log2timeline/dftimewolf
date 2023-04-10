#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the Turbinia processor."""

import unittest
import mock

from dftimewolf.lib.processors import turbinia_base_api

YARA_RULE = """rule dummy { condition: false }"""

class TurbiniaBaseTest(unittest.TestCase):
  """Tests for the Turbinia processor."""
  def setUp(self):
    """Tests that the processor can be initialized."""
    self.logger = mock.MagicMock()
    self.turbinia_processor = turbinia_base_api.TurbiniaAPIProcessorBase(
        self.logger
    )

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
    """Write a test to mock a call to TrubiniaStart."""
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


if __name__ == "__main__":
  unittest.main()
