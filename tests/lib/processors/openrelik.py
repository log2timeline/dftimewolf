"""Tests for the OpenRelik processor."""

import unittest
from unittest import mock

from openrelik_api_client import api_client, folders, workflows

from dftimewolf.lib.containers import containers
from dftimewolf.lib.processors import openrelik as openrelik_processor
from tests.lib import modules_test_base


class OpenRelikProcessorTest(modules_test_base.ModuleTestBase):
  """Tests for the OpenRelik processor."""

  # For pytype
  _module: openrelik_processor.OpenRelikProcessor

  def setUp(self):
    self._InitModule(openrelik_processor.OpenRelikProcessor)
    super().setUp()

  @mock.patch("openrelik_api_client.workflows.WorkflowsAPI.get_workflow")
  # pylint: disable=line-too-long
  @mock.patch(
    "dftimewolf.lib.processors.openrelik.OpenRelikProcessor.DownloadWorkflowOutput"
  )
  def testPollWorkflowStatus(self, mock_download_workflow, mock_get_workflow):
    """Tests that the workflow status is polled until completion."""

    # Create some fake data for a failed workflow
    fake_workflow = {
      "tasks": [
        {"status_short": "FAILURE"},
      ]
    }

    mock_get_workflow.return_value = fake_workflow
    mock_download_workflow.return_value = "fake_path"
    self._module.folder_id = 123
    self._module.openrelik_workflow_client = workflows.WorkflowsAPI(
      api_client.APIClient("fake_api", "fake_key")
    )
    status_generator = self._module.PollWorkflowStatus(456)
    self._AssertNoErrors()

    # Create some fake data for a successful workflow
    fake_workflow = {
      "tasks": [
        {"status_short": "SUCCESS"},
        {"output_files": [{"id": 1, "display_name": "fake_path"}]},
      ]
    }
    mock_get_workflow.return_value = fake_workflow
    status_generator = self._module.PollWorkflowStatus(456)
    self.assertEqual(next(status_generator), "fake_path")

  @mock.patch("openrelik_api_client.folders.FoldersAPI.update_folder")
  @mock.patch("openrelik_api_client.api_client.APIClient.download_file")
  @mock.patch("openrelik_api_client.workflows.WorkflowsAPI.create_workflow")
  @mock.patch("openrelik_api_client.api_client.APIClient.upload_file")
  @mock.patch("openrelik_api_client.folders.FoldersAPI.folder_exists")
  @mock.patch(
    "dftimewolf.lib.processors.openrelik.OpenRelikProcessor.PollWorkflowStatus"
  )
  @mock.patch("openrelik_api_client.workflows.WorkflowsAPI.run_workflow")
  def testProcess(
    self,
    mock_run_workflow,
    mock_poll,
    mock_folder_exists,
    mock_upload_file,
    mock_create_workflow,
    mock_download_file,
    mock_update_folder,
  ):
    """Tests the Process method."""
    # Set up the mocks
    mock_update_folder.return_value = None
    mock_upload_file.return_value = 1000
    mock_download_file.return_value = "fake_path"
    mock_folder_exists.return_value = True
    mock_create_workflow.return_value = 456
    mock_poll.return_value = "/local/path/test.plaso"
    mock_run_workflow.return_value = mock.Mock(status_code=200)
    self._module.openrelik_api = "http://fake_api:8710"
    self._module.openrelik_ui = "http://fake_api:8711"
    self._module.openrelik_api_key = "fake_key"
    self._module.folder_id = 123
    self._module.template_workflow_id = 1
    self._module.openrelik_workflow_client = workflows.WorkflowsAPI(
      api_client.APIClient(
        self._module.openrelik_api,
        self._module.openrelik_api_key,
      )
    )
    self._module.openrelik_folder_client = folders.FoldersAPI(
      api_client.APIClient(
        self._module.openrelik_api,
        self._module.openrelik_api_key,
      )
    )
    self._module.openrelik_api_client = api_client.APIClient(
      self._module.openrelik_api,
      self._module.openrelik_api_key,
    )
    test_path = "/test/path/*.plaso"

    self._module.StoreContainer(
      containers.File(name="fake_path", path=test_path)
    )
    self._ProcessModule()

    # (folder_id, [file_id], template_id)
    mock_create_workflow.assert_called_with(123, [1000], 1)

    mock_run_workflow.assert_called_once()

  @mock.patch("openrelik_api_client.api_client.APIClient.download_file")
  def testDownloadWorkflowOutput(self, _):
    """Tests the DownloadWorkflowOutput method."""
    # Set up mocks
    self._module.openrelik_api_client = mock.MagicMock()
    self._module.openrelik_api_client.base_url = "http://fake_api:8711"
    self._module.openrelik_api_client.download_file.return_value = (
      "fake_filepath"
    )

    with mock.patch.object(self._module.logger, 'info') as mock_log_info:
      # Call the method
      local_path = self._module.DownloadWorkflowOutput(123,
                                                       "test_filename.plaso")
    self._module.openrelik_api_client.download_file.assert_called_with(
      123, "test_filename.plaso"
    )
    mock_log_info.assert_called_with(
      "Saved output for file ID 123 to fake_filepath"
    )
    self.assertEqual(local_path, "fake_filepath")


if __name__ == "__main__":
  unittest.main()
