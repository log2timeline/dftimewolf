"""Tests the Turbinia processor."""

import unittest
import json
import os
import mock

import turbinia_api_lib

from google.oauth2.credentials import Credentials

from dftimewolf.lib.processors import turbinia_base
from dftimewolf import config
from dftimewolf.lib import state

YARA_RULE = """rule dummy { condition: false }"""
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
TASK_ID = "3a5759372b594c0bb2a81cda805ca9a0"
# pylint: disable=line-too-long
TEST_TASK_PATH = "/mnt/turbiniavolume/output/3a5759372b594c0bb2a81cda805ca9a0/1680565159-c4e9abd577db475484b2ded34a011b96-PlasoParserTask/c4e9abd577db475484b2ded34a011b96.plaso"
FAKE_CREDENTIALS = {
  "client_id": "fake_id.apps.googleusercontent.com",
  "client_secret": "fake_test_secret",
  "expiry": "2023-07-13T21:37:53.231458Z",
  "refresh_token": "fake_refresh_token",
  "scopes": [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email"
  ],
  "token": "fake_id_token",
  "token_uri": "https://oauth2.googleapis.com/token"
}

class TurbiniaBaseTest(unittest.TestCase):
  """Tests for the Turbinia processor."""

  def setUp(self):
    """Tests that the processor can be initialized."""
    self.logger = mock.MagicMock()
    test_state = state.DFTimewolfState(config.Config)
    self.turbinia_processor = turbinia_base.TurbiniaProcessorBase(
        test_state, self.logger)
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
    self.assertEqual(
        self.turbinia_processor.turbinia_api, "http://localhost:8001")
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
    mock_api_instance = mock.MagicMock()
    mock_api_instance.create_request = mock_create_request
    self.turbinia_processor.requests_api_instance = mock_api_instance
    evidence = {
        "type": "GoogleCloudDisk",
        "disk_name": "disk-1",
        "project": "project-1",
        "zone": "us-central1-f",
    }
    request_id = self.turbinia_processor.TurbiniaStart(
        evidence=evidence, yara_rules=YARA_RULE)
    self.assertEqual(request_id, "41483253079448e59685d88f37ab91f7")

  # pylint: disable=line-too-long
  @mock.patch(
      "turbinia_api_lib.api.turbinia_requests_api.TurbiniaRequestsApi.get_request_status"
  )
  @mock.patch("time.sleep")
  def testTurbiniaWait(self, mock_get_request_status, _):
    """Tests the TurbiniaWait method."""
    mock_api_instance = mock.MagicMock()
    mock_api_instance.create_request = mock_get_request_status
    self.turbinia_processor.requests_api_instance = mock_api_instance
    mock_get_request_status.return_value = self._request_status
    for task, path in self.turbinia_processor.TurbiniaWait(TASK_ID):
      # Check that the task and path are correct for a PlasoParserTask
      if task["id"] == TASK_ID:
        self.assertEqual(task, self._request_status["tasks"][0])
        self.assertEqual(path, TEST_TASK_PATH)
      break

  def testIsInterestingPath(self):
    """Tests the _isInterestingPath method."""
    # pylint: disable=protected-access
    self.assertTrue(self.turbinia_processor._isInterestingPath(TEST_TASK_PATH))

  @mock.patch('tempfile.mkdtemp')
  def testExtractPath(self, mock_tempdir):
    """Tests the _ExtractFiles method."""
    mock_tempdir.return_value = '/tmp'
    file_path = os.path.join(
        CURRENT_DIR, "test_data", "c4e9abd577db475484b2ded34a011b96.tgz")
    expected_local_path = f"/tmp{TEST_TASK_PATH}"
    # pylint: disable=protected-access
    local_path = self.turbinia_processor._ExtractFiles(
        file_path, TEST_TASK_PATH)
    self.assertEqual(local_path, expected_local_path)

  @mock.patch('dftimewolf.lib.processors.turbinia_base.TurbiniaProcessorBase.GetCredentials')
  @mock.patch('dftimewolf.lib.processors.turbinia_base.TurbiniaProcessorBase.InitializeTurbiniaApiClient')
  def testRefreshClientCredentials(self,
                                   mock_get_credentials, mock_initialize_client):
    """Tests the RefreshClientCredentials method."""
    # Set an expired token.
    self.turbinia_processor.credentials = mock.MagicMock(
        expiry = FAKE_CREDENTIALS['expiry'], expired = True)
    self.turbinia_processor.RefreshClientCredentials()
    mock_get_credentials.assert_called_once()
    mock_initialize_client.assert_called_once()

  @mock.patch('dftimewolf.lib.processors.turbinia_base.TurbiniaProcessorBase.GetCredentials')
  def testInitializeTurbiniaApiClientNoCreds(self, mock_get_credentials):
    """Tests the InitializeTurbiniaApiClient method."""
    self.turbinia_processor.turbinia_api = 'http://127.0.0.1:8000'
    self.turbinia_processor.turbinia_auth = True
    mock_credentials = mock.MagicMock(spec=Credentials, id_token = FAKE_CREDENTIALS['token'])
    mock_credentials.id_token = mock.MagicMock()
    mock_credentials.id_token.return_value = FAKE_CREDENTIALS['token']
    self.turbinia_processor.credentials = mock_credentials
    mock_get_credentials.return_value = mock_credentials
    result = self.turbinia_processor.InitializeTurbiniaApiClient(None)
    mock_get_credentials.assert_called_once()
    self.assertIsInstance(result, turbinia_api_lib.api_client.ApiClient)

  @mock.patch('dftimewolf.lib.processors.turbinia_base.TurbiniaProcessorBase.GetCredentials')
  def testInitializeTurbiniaApiClient(self, mock_get_credentials):
    """Tests the InitializeTurbiniaApiClient method."""
    self.turbinia_processor.turbinia_api = 'http://127.0.0.1:8000'
    self.turbinia_processor.turbinia_auth = True
    mock_credentials = mock.MagicMock(spec=Credentials, id_token = FAKE_CREDENTIALS['token'])
    mock_credentials.id_token = mock.MagicMock()
    mock_credentials.id_token.return_value = FAKE_CREDENTIALS['token']
    self.turbinia_processor.credentials = mock_credentials
    mock_get_credentials.return_value = mock_credentials
    result = self.turbinia_processor.InitializeTurbiniaApiClient(mock_credentials)
    mock_get_credentials.assert_not_called()
    self.assertIsInstance(result, turbinia_api_lib.api_client.ApiClient)

if __name__ == "__main__":
  unittest.main()
