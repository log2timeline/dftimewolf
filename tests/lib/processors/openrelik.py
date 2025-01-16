"""Tests for the OpenRelik processor."""

import unittest
from unittest import mock

from openrelik_api_client import api_client, folders, workflows

from dftimewolf.lib import errors
from dftimewolf.lib.containers import containers
from dftimewolf.lib.processors import openrelik as openrelik_processor
from tests.lib import modules_test_base


class OpenRelikProcessorTest(modules_test_base.ModuleTestBase):
  """Tests for the OpenRelik processor."""

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
    self.assertRaises(errors.DFTimewolfError, next, status_generator)

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
  ):
    """Tests the Process method."""
    # Set up the mocks
    mock_upload_file.return_value = 1000
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
        containers.File(name="fake_path", path=test_path))
    self._ProcessModule()

    # (folder_id, [file_id], template_id)
    mock_create_workflow.assert_called_with(123, [1000], 1)

    mock_run_workflow.assert_called_once()

  @mock.patch("dftimewolf.lib.processors.openrelik.tempfile.NamedTemporaryFile")
  @mock.patch(
    "dftimewolf.lib.processors.openrelik.OpenRelikProcessor.PublishMessage"
  )
  def testDownloadWorkflowOutput(self, mock_publish, mock_tempfile):
    """Tests the DownloadWorkflowOutput method."""
    # Set up mocks
    mock_response = mock.Mock()
    mock_response.text = "fake content"
    self._module.openrelik_api_client = mock.MagicMock()
    self._module.openrelik_api_client.base_url = "http://fake_api:8711"
    self._module.openrelik_api_client.session.get.return_value = (
      mock_response
    )

    mock_tempfile_object = mock.MagicMock()
    mock_tempfile_object.name = "fake_filepath"
    mock_tempfile.return_value = mock_tempfile_object

    # Call the method
    local_path = self._module.DownloadWorkflowOutput(
      123, "test_filename.plaso"
    )

    # pylint: disable=line-too-long
    self._module.openrelik_api_client.session.get.assert_called_with(
      f"{self._module.openrelik_api_client.base_url}/files/123/download"
    )
    mock_tempfile.assert_called_with(
      mode="wb", prefix="test_filename", suffix=".plaso", delete=False
    )

    mock_tempfile_object.write.assert_called_with(b"fake content")
    mock_publish.assert_called_with(
      "Saving output for file ID 123 to fake_filepath"
    )

    self.assertEqual(local_path, "fake_filepath")



if __name__ == "__main__":
  unittest.main()
