"""Tests for the OpenRelik processor."""

import unittest
from unittest import mock

from openrelik_api_client import api_client, folders, workflows


from dftimewolf.lib import state as state_lib
from dftimewolf.lib import errors
from dftimewolf.lib.containers import containers
from dftimewolf.lib.processors import openrelik as openrelik_processor


class OpenRelikProcessorTest(unittest.TestCase):
  """Tests for the OpenRelik processor."""

  def setUp(self):
    """Tests that the processor can be initialized."""
    self.test_state = state_lib.DFTimewolfState(None)
    self.openrelik_module = openrelik_processor.OpenRelikProcessor(
      self.test_state
    )
    self.assertIsNotNone(self.openrelik_module)

  @mock.patch("openrelik_api_client.workflows.WorkflowsAPI.get_workflow")
  # pylint: disable=line-too-long
  @mock.patch(
    "dftimewolf.lib.processors.openrelik.OpenRelikProcessor.DownloadWorkflowOutput"
  )
  def testPollWorkflowStatus(self, mock_download_workflow, mock_get_workflow):
    """Tests that the workflow status is polled until completion."""

    # Create some fake data for a workflow
    fake_workflow = {
      "tasks": [
        {"status_short": "FAILED"},
      ]
    }

    mock_get_workflow.return_value = fake_workflow
    mock_download_workflow.return_value = "fake_path"
    self.openrelik_module.folder_id = 123
    self.openrelik_module.openrelik_workflow_client = workflows.WorkflowsAPI(
      api_client.APIClient("fake_api", "fake_key")
    )
    status_generator = self.openrelik_module.PollWorkflowStatus(456)
    self.assertRaises(errors.DFTimewolfError, next, status_generator)

    # Create some fake data for a workflow
    fake_workflow = {
      "tasks": [
        {"status_short": "SUCCESS"},
        {"output_files": [{"id": 1, "display_name": "fake_path"}]},
      ]
    }
    mock_get_workflow.return_value = fake_workflow
    status_generator = self.openrelik_module.PollWorkflowStatus(456)
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
    mock_create_workflow.return_value = {"id": 456}
    mock_poll.return_value = "/local/path/test.plaso"
    mock_run_workflow.return_value = mock.Mock(status_code=200)
    self.openrelik_module.openrelik_api = "http://fake_api:8710"
    self.openrelik_module.openrelik_ui = "http://fake_api:8711"
    self.openrelik_module.openrelik_api_key = "fake_key"
    self.openrelik_module.folder_id = 123
    self.openrelik_module.workflow_id = 1
    self.openrelik_module.openrelik_workflow_client = workflows.WorkflowsAPI(
      api_client.APIClient(
        self.openrelik_module.openrelik_api,
        self.openrelik_module.openrelik_api_key,
      )
    )
    self.openrelik_module.openrelik_folder_client = folders.FoldersAPI(
      api_client.APIClient(
        self.openrelik_module.openrelik_api,
        self.openrelik_module.openrelik_api_key,
      )
    )
    self.openrelik_module.openrelik_api_client = api_client.APIClient(
      self.openrelik_module.openrelik_api,
      self.openrelik_module.openrelik_api_key,
    )
    test_path = "/test/path/*.plaso"
    fake_container = containers.File(name="fake_path", path=test_path)
    self.openrelik_module.Process(fake_container)

    # (folder_id, [file_id], template_id)
    mock_create_workflow.assert_called_with(123, [1000], 1)

    mock_run_workflow.assert_called_once()


if __name__ == "__main__":
  unittest.main()
