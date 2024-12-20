"""Tests for the OpenRelik processor."""

import unittest
from unittest import mock

from openrelik_api_client import api_client, folders, workflows


from dftimewolf.lib import state as state_lib
from dftimewolf.lib import errors
from dftimewolf.lib.processors import openrelik as openrelik_processor


class OpenRelikProcessorTest(unittest.TestCase):
  """Tests for the OpenRelik processor."""

  def setUp(self):
    """Tests that the processor can be initialized."""
    self.test_state = state_lib.DFTimewolfState(None)
    self.openrelik_module = openrelik_processor.OpenRelikProcessor(self.test_state)
    self.assertIsNotNone(self.openrelik_module)

  @mock.patch(
      "openrelik_api_client.workflows.WorkflowsAPI.get_workflow"
  )
  @mock.patch('dftimewolf.lib.processors.openrelik.OpenRelikProcessor.DownloadWorkflowOutput')
  def testPollWorkflowStatus(self, mock_download_workflow, mock_get_workflow):
    """Tests that the workflow status is polled until completion."""

    # Create some fake data for a workflow
    fake_workflow = {
        'tasks': [
            {'status_short': "FAILED"},
        ]
    }

    mock_get_workflow.return_value = fake_workflow
    mock_download_workflow.return_value = "fake_path"
    self.openrelik_module.folder_id = 123
    self.openrelik_module.openrelik_workflow_client = workflows.WorkflowsAPI(
        api_client.APIClient("fake_api", "fake_key")
    )
    status_generator = self.openrelik_module.PollWorkflowStatus(456)
    self.assertRaises(
       errors.DFTimewolfError, next, status_generator
    )

    # Create some fake data for a workflow
    fake_workflow = {
        'tasks': [
            {'status_short': "SUCCESS"},
            {'output_files': [ {'id': 1, 'display_name': 'fake_path'}] }
        ]
    }
    mock_get_workflow.return_value = fake_workflow
    status_generator = self.openrelik_module.PollWorkflowStatus(456)
    self.assertEqual(next(status_generator), 'fake_path')


if __name__ == "__main__":
  unittest.main()
