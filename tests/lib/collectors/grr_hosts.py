#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR host collectors."""

import unittest
import six
import mock

from grr_response_proto import flows_pb2
from grr_api_client import errors as grr_errors

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.collectors import grr_hosts
from dftimewolf.lib.errors import DFTimewolfError

from tests.lib.collectors.test_data import mock_grr_hosts


# Extensive access to protected members for testing, and mocking of classes.
# pylint: disable=protected-access,invalid-name
class GRRFlowTests(unittest.TestCase):
  """Tests for the GRRFlow base class."""

  def setUp(self):
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_flow_module = grr_hosts.GRRFlow(self.test_state)
    self.grr_flow_module.SetUp(
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin1',
        grr_password='admin2',
        approvers='approver1@example.com,approver2@example.com',
        verify=True
    )

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self.grr_flow_module)

  @mock.patch('grr_api_client.api.GrrApi.SearchClients')
  def testGetClientByHostname(self, mock_SearchClients):
    """Tests that GetClientByHostname fetches the most recent GRR client."""
    mock_SearchClients.return_value = mock_grr_hosts.MOCK_CLIENT_LIST
    client = self.grr_flow_module._GetClientByHostname('tomchop')
    mock_SearchClients.assert_called_with('tomchop')
    self.assertEqual(
        client.data.client_id, mock_grr_hosts.MOCK_CLIENT_RECENT.data.client_id)

  @mock.patch('grr_api_client.api.GrrApi.SearchClients')
  def testGetClientByHostnameError(self, mock_SearchClients):
    """Tests that GetClientByHostname fetches the most recent GRR client."""
    mock_SearchClients.side_effect = grr_errors.UnknownError
    self.grr_flow_module._GetClientByHostname('tomchop')
    self.assertEqual(len(self.test_state.errors), 1)
    self.assertEqual(
        self.test_state.errors[0],
        ('Could not search for host tomchop: ', True)
    )

  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  def testLaunchFlow(self, mock_CreateFlow):
    """Tests that CreateFlow is correctly called."""
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    flow_id = self.grr_flow_module._LaunchFlow(
        mock_grr_hosts.MOCK_CLIENT, "FlowName", "FlowArgs")
    self.assertEqual(flow_id, 'F:12345')
    mock_CreateFlow.assert_called_once_with(name="FlowName", args="FlowArgs")

  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  def testLaunchFlowKeepalive(self, mock_CreateFlow):
    """Tests that keepalive flows are correctly created."""
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    self.grr_flow_module.keepalive = True
    flow_id = self.grr_flow_module._LaunchFlow(
        mock_grr_hosts.MOCK_CLIENT, "FlowName", "FlowArgs")
    self.assertEqual(flow_id, 'F:12345')
    self.assertEqual(mock_CreateFlow.call_count, 2)
    self.assertEqual(
        mock_CreateFlow.call_args,
        ((), {'name': 'KeepAlive', 'args': flows_pb2.KeepAliveArgs()}))

  @mock.patch('grr_api_client.flow.FlowRef.Get')
  def testAwaitFlow(self, mock_FlowGet):
    """Test that no errors are generated when GRR flow succeeds."""
    mock_FlowGet.return_value = mock_grr_hosts.MOCK_FLOW
    self.grr_flow_module._AwaitFlow(mock_grr_hosts.MOCK_CLIENT, "F:12345")
    mock_FlowGet.assert_called_once()
    self.assertEqual(self.test_state.errors, [])

  @mock.patch('grr_api_client.flow.FlowRef.Get')
  def testAwaitFlowError(self, mock_FlowGet):
    """Test that an exception is raised when flow has an ERROR status."""
    mock_FlowGet.return_value = mock_grr_hosts.MOCK_FLOW_ERROR
    error_msg = 'F:12345: FAILED! Message from GRR:'
    with six.assertRaisesRegex(self, DFTimewolfError, error_msg):
      self.grr_flow_module._AwaitFlow(mock_grr_hosts.MOCK_CLIENT, "F:12345")

  @mock.patch('grr_api_client.flow.FlowRef.Get')
  def testAwaitFlowGRRError(self, mock_FlowGet):
    """"Test that an exception is raised if the GRR API raises an error."""
    mock_FlowGet.side_effect = grr_errors.UnknownError
    error_msg = 'Unable to stat flow F:12345 for host'
    with six.assertRaisesRegex(self, DFTimewolfError, error_msg):
      self.grr_flow_module._AwaitFlow(mock_grr_hosts.MOCK_CLIENT, "F:12345")

  @mock.patch('os.remove')
  @mock.patch('os.path.isdir')
  @mock.patch('os.makedirs')
  @mock.patch('zipfile.ZipFile')
  @mock.patch('grr_api_client.flow.FlowBase.GetFilesArchive')
  def testDownloadFilesForFlow(self, mock_GetFilesArchive, mock_ZipFile,
                               mock_makedirs, mock_isdir, mock_remove):
    """Tests that files are downloaded and unzipped in the correct
    directories."""
    # Change output_path to something constant so we can easily assert
    # if calls were done correctly.
    self.grr_flow_module.output_path = '/tmp/random'
    mock_isdir.return_value = False  # Return false so makedirs is called

    return_value = self.grr_flow_module._DownloadFiles(
        mock_grr_hosts.MOCK_CLIENT, "F:12345")
    self.assertEqual(return_value, '/tmp/random/tomchop')
    mock_GetFilesArchive.assert_called_once()
    mock_ZipFile.assert_called_once_with('/tmp/random/F:12345.zip')
    mock_isdir.assert_called_once_with('/tmp/random/tomchop')
    mock_makedirs.assert_called_once_with('/tmp/random/tomchop')
    mock_remove.assert_called_once_with('/tmp/random/F:12345.zip')

  @mock.patch('os.path.exists')
  @mock.patch('grr_api_client.flow.FlowBase.GetFilesArchive')
  def testNotDownloadFilesForExistingFlow(self, mock_GetFilesArchive,
                                          mock_exists):
    """Tests that files are downloaded and unzipped in the correct
    directories."""
    # Change output_path to something constant so we can easily assert
    # if calls were done correctly.
    self.grr_flow_module.output_path = '/tmp/random'
    mock_exists.return_value = True  # Simulate existing flow directory

    self.grr_flow_module._DownloadFiles(mock_grr_hosts.MOCK_CLIENT, "F:12345")
    mock_GetFilesArchive.assert_not_called()

class GRRArtifactCollectorTest(unittest.TestCase):
  """Tests for the GRR artifact collector."""

  def setUp(self):
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_artifact_collector = grr_hosts.GRRArtifactCollector(
        self.test_state)
    self.grr_artifact_collector.SetUp(
        hosts='tomchop,tomchop2',
        artifacts=None,
        extra_artifacts=None,
        use_tsk=True,
        reason='Random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        approvers='approver1,approver2',
        verify=False
    )

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self.grr_artifact_collector)

  def testSetup(self):
    """Tests that the module is setup properly."""
    self.assertEqual(self.grr_artifact_collector.artifacts, [])
    self.assertEqual(
        self.grr_artifact_collector.extra_artifacts, [])
    self.assertEqual(self.grr_artifact_collector.hostnames,
                     ['tomchop', 'tomchop2'])
    self.assertTrue(self.grr_artifact_collector.use_tsk)

  @mock.patch('grr_api_client.flow.FlowRef.Get')
  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('grr_response_proto.flows_pb2.ArtifactCollectorFlowArgs')
  @mock.patch('grr_api_client.api.GrrApi.SearchClients')
  def testProcessSpecificArtifacts(self,
                                   mock_SearchClients,
                                   mock_ArtifactCollectorFlowArgs,
                                   mock_DownloadFiles,
                                   mock_CreateFlow,
                                   mock_Get):
    """Tests that artifacts defined during setup are searched for."""
    mock_DownloadFiles.return_value = '/tmp/tmpRandom/tomchop'
    mock_SearchClients.return_value = mock_grr_hosts.MOCK_CLIENT_LIST
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    mock_Get.return_value = mock_grr_hosts.MOCK_FLOW
    self.grr_artifact_collector = grr_hosts.GRRArtifactCollector(
        self.test_state)
    self.grr_artifact_collector.SetUp(
        hosts='tomchop,tomchop2',
        artifacts='RandomArtifact',
        extra_artifacts='AnotherArtifact',
        use_tsk=True,
        reason='Random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        approvers='approver1,approver2',
        verify=False
    )
    self.grr_artifact_collector.Process()
    kwargs = mock_ArtifactCollectorFlowArgs.call_args[1]
    # raise ValueError(str(kwargs[1]))
    self.assertFalse(kwargs['apply_parsers'])  # default argument
    self.assertTrue(kwargs['ignore_interpolation_errors'])  # default argument
    self.assertTrue(kwargs['use_tsk'])
    sorted_artifacts = sorted(['AnotherArtifact', 'RandomArtifact'])
    self.assertEqual(sorted(kwargs['artifact_list']), sorted_artifacts)

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('grr_api_client.flow.FlowBase.Get')
  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  @mock.patch('grr_api_client.api.GrrApi.SearchClients')
  def testProcess(self, mock_SearchClients, mock_CreateFlow, mock_Get,
                  mock_DownloadFiles):
    """Tests that the module is setup properly."""
    mock_SearchClients.return_value = mock_grr_hosts.MOCK_CLIENT_LIST
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    mock_DownloadFiles.return_value = '/tmp/tmpRandom/tomchop'
    mock_Get.return_value = mock_grr_hosts.MOCK_FLOW
    self.grr_artifact_collector.Process()
    # Flow ID is F:12345, Client ID is C.0000000000000001
    mock_SearchClients.assert_any_call('tomchop')
    mock_SearchClients.assert_any_call('tomchop2')
    self.assertEqual(mock_CreateFlow.call_count, 1)
    self.assertEqual(mock_DownloadFiles.call_count, 1)
    mock_DownloadFiles.assert_called_with(
        mock_grr_hosts.MOCK_CLIENT_LIST[1], mock_grr_hosts.MOCK_FLOW.flow_id
    )
    self.assertEqual(len(self.test_state.output), 1)
    self.assertEqual(self.test_state.output[0][0], 'tomchop')
    self.assertEqual(self.test_state.output[0][1], '/tmp/tmpRandom/tomchop')


class GRRFileCollectorTest(unittest.TestCase):
  """Tests for the GRR file collector."""

  def setUp(self):
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_file_collector = grr_hosts.GRRFileCollector(self.test_state)
    self.grr_file_collector.SetUp(
        hosts='tomchop,tomchop2',
        files='/etc/passwd',
        use_tsk=True,
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        action='stat'
    )

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self.grr_file_collector)
    self.assertEqual(self.grr_file_collector.hostnames,
                     ['tomchop', 'tomchop2'])
    self.assertEqual(self.grr_file_collector.files, ['/etc/passwd'])

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('grr_api_client.api.GrrApi.SearchClients')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  def testProcess(self,
                  mock_LaunchFlow,
                  mock_SearchClients,
                  mock_DownloadFiles,
                  _):
    """Tests that processing launches appropriate flows."""
    mock_SearchClients.return_value = mock_grr_hosts.MOCK_CLIENT_LIST
    mock_DownloadFiles.return_value = '/tmp/something'
    self.grr_file_collector.Process()
    mock_LaunchFlow.assert_called_with(
        mock_grr_hosts.MOCK_CLIENT_RECENT,
        'FileFinder',
        flows_pb2.FileFinderArgs(
            paths=['/etc/passwd'],
            action=flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.STAT)
        )
    )
    self.assertEqual(self.test_state.output[0], ('tomchop', '/tmp/something'))


class GRRFlowCollector(unittest.TestCase):
  """Tests for the GRR flow collector."""

  def setUp(self):
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_flow_collector = grr_hosts.GRRFlowCollector(self.test_state)
    self.grr_flow_collector.SetUp(
        host='tomchop',
        flow_id='F:12345',
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2'
    )

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow')
  @mock.patch('grr_api_client.api.GrrApi.SearchClients')
  def testProcess(self,
                  mock_SearchClients,
                  _,
                  mock_DownloadFiles):
    """Tests that the collector can be initialized."""
    mock_SearchClients.return_value = mock_grr_hosts.MOCK_CLIENT_LIST
    mock_DownloadFiles.return_value = '/tmp/something'
    self.grr_flow_collector.Process()
    mock_DownloadFiles.assert_called_once_with(
        mock_grr_hosts.MOCK_CLIENT_RECENT, 'F:12345')
    self.assertEqual(self.test_state.output[0], ('tomchop', '/tmp/something'))


class GRRTimelineCollector(unittest.TestCase):
  """Tests for the GRR flow collector."""

  def setUp(self):
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_timeline_collector = grr_hosts.GRRTimelineCollector(
        self.test_state)
    self.grr_timeline_collector.SetUp(
        hosts='tomchop',
        root_path='/',
        reason='random reason',
        timeline_format='1',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2'
    )

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self.grr_timeline_collector)
    self.assertEqual(self.grr_timeline_collector.hostnames,
                     ['tomchop'])
    self.assertEqual(self.grr_timeline_collector.root_path, b'/')
    self.assertEqual(self.grr_timeline_collector._timeline_format, 1)

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.'
              'GRRTimelineCollector._DownloadTimeline')
  # mock grr_api_client.flow.FlowBase.GetCollectedTimeline instead once when it
  # becomes available in pypi
  @mock.patch('grr_api_client.flow.FlowBase.Get')
  @mock.patch('grr_api_client.api.GrrApi.SearchClients')
  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  def testProcess(self,
                  mock_CreateFlow,
                  mock_SearchClients,
                  mock_Get,
                  mock_DownloadTimeline):
    """Tests that the collector can be initialized."""
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    mock_SearchClients.return_value = mock_grr_hosts.MOCK_CLIENT_LIST
    mock_DownloadTimeline.return_value = '/tmp/something'
    mock_Get.return_value = mock_grr_hosts.MOCK_FLOW
    self.grr_timeline_collector.Process()
    mock_DownloadTimeline.assert_called_once_with(
        mock_grr_hosts.MOCK_CLIENT_RECENT, 'F:12345')
    self.assertEqual(self.test_state.output[0], ('tomchop', '/tmp/something'))

if __name__ == '__main__':
  unittest.main()
