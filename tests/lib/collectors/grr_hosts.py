#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR host collectors."""

import unittest

import mock
import six

import pandas as pd
from grr_api_client import errors as grr_errors
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import osquery_pb2
from tests.lib.collectors.test_data import mock_grr_hosts

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib import errors
from dftimewolf.lib.collectors import grr_hosts
from dftimewolf.lib.containers import containers
from dftimewolf.lib.errors import DFTimewolfError


# Extensive access to protected members for testing, and mocking of classes.
# pylint: disable=protected-access,invalid-name,arguments-differ
# @mock.patch('grr_api_client.api.InitHttp')
class GRRFlowTests(unittest.TestCase):
  """Tests for the GRRFlow base class."""

  # For pytype
  grr_flow_module: grr_hosts.GRRFlow
  mock_grr_api: mock.Mock
  test_state: state.DFTimewolfState

  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp):
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_flow_module = grr_hosts.GRRFlow(self.test_state)
    self.grr_flow_module.SetUp(
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin1',
        grr_password='admin2',
        approvers='approver1@example.com,approver2@example.com',
        verify=True,
        skip_offline_clients=False
    )
    self.grr_flow_module._CHECK_FLOW_INTERVAL_SEC = 1

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self.grr_flow_module)

  def testGetClientBySelector(self):
    """Tests that GetClientBySelector fetches the most recent GRR client."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    client = self.grr_flow_module._GetClientBySelector('C.0000000000000001')
    self.mock_grr_api.SearchClients.assert_called_with('C.0000000000000001')
    self.assertEqual(client.data.client_id, 'C.0000000000000001')

  def testGetClientByUsername(self):
    """Tests that GetClientBySelector fetches the correct GRR client."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    client = self.grr_flow_module._GetClientBySelector('tomchop_username2')
    self.mock_grr_api.SearchClients.assert_called_with('tomchop_username2')
    self.assertEqual(client.data.client_id, 'C.0000000000000001')

  def testGetClientBySelectorError(self):
    """Tests that GetClientBySelector fetches the most recent GRR client."""
    self.mock_grr_api.SearchClients.side_effect = grr_errors.UnknownError
    with self.assertRaises(errors.DFTimewolfError) as error:
      self.grr_flow_module._GetClientBySelector('tomchop')
    self.assertEqual(
        'Could not search for host tomchop: ', error.exception.message)
    self.assertEqual(len(self.test_state.errors), 1)

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
  def testAwaitFlowOffline(self, mock_FlowGet):
    """Test that flows on offline hosts will be abandoned."""
    mock_FlowGet.return_value = mock_grr_hosts.MOCK_FLOW_RUNNING
    mock_FlowGet.return_value.state = 0
    self.grr_flow_module.skip_offline_clients = True
    self.grr_flow_module._AwaitFlow(mock_grr_hosts.MOCK_CLIENT, "F:12345")
    mock_FlowGet.assert_called_once()
    self.assertEqual(self.test_state.errors, [])
    self.assertEqual(
        self.grr_flow_module._skipped_flows,
        [('C.0000000000000000', 'F:12345')])
    self.grr_flow_module.skip_offline_clients = False

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
    error_msg = 'Unknown error retrieving flow F:12345 for host'
    with six.assertRaisesRegex(self, DFTimewolfError, error_msg):
      self.grr_flow_module._AwaitFlow(mock_grr_hosts.MOCK_CLIENT, "F:12345")

  @mock.patch('os.remove')
  @mock.patch('os.path.isdir')
  @mock.patch('os.makedirs')
  @mock.patch('zipfile.ZipFile')
  @mock.patch('grr_api_client.flow.FlowBase.GetFilesArchive')
  @mock.patch('grr_api_client.flow.FlowBase.Get')
  def testDownloadArtifactFilesForFlow(self, mock_Get, mock_GetFilesArchive,
                                       mock_ZipFile, mock_makedirs, mock_isdir,
                                       mock_remove):
    """Test if results are downloaded & unzipped in the correct directories."""
    # Change output_path to something constant so we can easily assert
    # if calls were done correctly.
    self.grr_flow_module.output_path = '/tmp/random'
    mock_isdir.return_value = False  # Return false so makedirs is called
    mock_Get.return_value.data.name = 'ArtifactFlow'

    return_value = self.grr_flow_module._DownloadFiles(
        mock_grr_hosts.MOCK_CLIENT, 'F:12345')
    self.assertEqual(return_value, '/tmp/random/tomchop/F:12345')
    mock_GetFilesArchive.assert_called_once()
    mock_ZipFile.assert_called_once_with('/tmp/random/F:12345.zip')
    mock_isdir.assert_called_once_with('/tmp/random/tomchop/F:12345')
    mock_makedirs.assert_called_once_with('/tmp/random/tomchop/F:12345')
    mock_remove.assert_called_once_with('/tmp/random/F:12345.zip')

  @mock.patch('os.remove')
  @mock.patch('os.path.isdir')
  @mock.patch('os.makedirs')
  @mock.patch('zipfile.ZipFile')
  @mock.patch('shutil.copy2')
  @mock.patch('grr_api_client.flow.FlowBase.GetFilesArchive')
  @mock.patch('grr_api_client.flow.FlowBase.GetCollectedTimelineBody')
  @mock.patch('grr_api_client.flow.FlowBase.Get')
  def testDownloadTimelineBodyForFlow(self, mock_Get,
                                      mock_GetCollectedTimelineBody,
                                      mock_GetFilesArchive, mock_copy2,
                                      mock_ZipFile, mock_makedirs, mock_isdir,
                                      mock_remove):
    """Tests if timeline results are downloaded in the correct directories."""
    # Change output_path to something constant so we can easily assert
    # if calls were done correctly.
    self.grr_flow_module.output_path = '/tmp/random'
    mock_isdir.return_value = False  # Return false so makedirs is called
    mock_Get.return_value.data.name = 'TimelineFlow'

    return_value = self.grr_flow_module._DownloadFiles(
        mock_grr_hosts.MOCK_CLIENT, 'F:12345')
    self.assertEqual(return_value, '/tmp/random/tomchop/F:12345')
    mock_GetCollectedTimelineBody.assert_called_once()
    mock_GetFilesArchive.assert_not_called()
    mock_ZipFile.assert_not_called()
    mock_copy2.assert_called_once_with(
        '/tmp/random/F:12345.body',
        '/tmp/random/tomchop/F:12345/F:12345_timeline.body')
    mock_isdir.assert_called_once_with('/tmp/random/tomchop/F:12345')
    mock_makedirs.assert_called_once_with('/tmp/random/tomchop/F:12345')
    mock_remove.assert_called_once_with('/tmp/random/F:12345.body')

  @mock.patch('os.path.exists')
  @mock.patch('grr_api_client.flow.FlowBase.GetFilesArchive')
  @mock.patch('grr_api_client.flow.FlowBase.GetCollectedTimelineBody')
  @mock.patch('grr_api_client.flow.FlowBase.Get')
  def testNotDownloadFilesForExistingFlow(self, _mock_Get,
                                          mock_GetCollectedTimelineBody,
                                          mock_GetFilesArchive, mock_exists):
    """Tests if results are not downloaded if the directory already exists."""
    # Change output_path to something constant so we can easily assert
    # if calls were done correctly.
    self.grr_flow_module.output_path = '/tmp/random'
    mock_exists.return_value = True  # Simulate existing flow directory

    self.grr_flow_module._DownloadFiles(mock_grr_hosts.MOCK_CLIENT, 'F:12345')
    mock_GetFilesArchive.assert_not_called()
    mock_GetCollectedTimelineBody.assert_not_called()

class GRRArtifactCollectorTest(unittest.TestCase):
  """Tests for the GRR artifact collector."""

  # For pytype
  grr_artifact_collector: grr_hosts.GRRArtifactCollector
  mock_grr_api: mock.Mock
  test_state: state.DFTimewolfState

  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp):
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_artifact_collector = grr_hosts.GRRArtifactCollector(
        self.test_state)
    self.grr_artifact_collector.SetUp(
        hostnames='C.0000000000000001',
        artifacts=None,
        extra_artifacts=None,
        use_raw_filesystem_access=False,
        reason='Random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        max_file_size=1234,
        approvers='approver1,approver2',
        verify=False,
        skip_offline_clients=False
    )

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self.grr_artifact_collector)

  def testSetup(self):
    """Tests that the module is setup properly."""
    # pytype: disable=attribute-error
    actual_hosts = [h.hostname for h in \
        self.grr_artifact_collector.state.GetContainers(
            self.grr_artifact_collector.GetThreadOnContainerType())]
    # pytype: enable=attribute-error

    self.assertEqual(self.grr_artifact_collector.artifacts, [])
    self.assertEqual(
        self.grr_artifact_collector.extra_artifacts, [])
    self.assertEqual(['C.0000000000000001'], actual_hosts)
    self.assertFalse(self.grr_artifact_collector.use_raw_filesystem_access)

  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch('grr_api_client.flow.FlowRef.Get')
  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('grr_response_proto.flows_pb2.ArtifactCollectorFlowArgs')
  def testProcessSpecificArtifacts(self,
                                   mock_ArtifactCollectorFlowArgs,
                                   mock_DownloadFiles,
                                   mock_CreateFlow,
                                   mock_Get,
                                   mock_InitHttp):
    """Tests that artifacts defined during setup are searched for."""
    mock_DownloadFiles.return_value = '/tmp/tmpRandom/tomchop'
    mock_InitHttp.return_value.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    mock_Get.return_value = mock_grr_hosts.MOCK_FLOW
    self.grr_artifact_collector = grr_hosts.GRRArtifactCollector(
        self.test_state)
    self.grr_artifact_collector.SetUp(
        hostnames='C.0000000000000001',
        artifacts='RandomArtifact',
        extra_artifacts='AnotherArtifact',
        use_raw_filesystem_access=False,
        reason='Random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        max_file_size=1234,
        approvers='approver1,approver2',
        verify=False,
        skip_offline_clients=False
    )

    self.grr_artifact_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_artifact_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_artifact_collector.Process(c)
    self.grr_artifact_collector.PostProcess()

    kwargs = mock_ArtifactCollectorFlowArgs.call_args[1]
    self.assertFalse(kwargs['apply_parsers'])  # default argument
    self.assertTrue(kwargs['ignore_interpolation_errors'])  # default argument
    self.assertFalse(kwargs['use_raw_filesystem_access'])
    self.assertEqual(kwargs['max_file_size'], 1234)
    sorted_artifacts = sorted(['AnotherArtifact', 'RandomArtifact'])
    self.assertEqual(sorted(kwargs['artifact_list']), sorted_artifacts)

  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch('grr_api_client.flow.FlowRef.Get')
  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('grr_response_proto.flows_pb2.ArtifactCollectorFlowArgs')
  def testProcessWindowsArtifacts(self,
                                   mock_ArtifactCollectorFlowArgs,
                                   mock_DownloadFiles,
                                   mock_CreateFlow,
                                   mock_Get,
                                   mock_InitHttp):
    """Tests that artifacts are obtained in raw mode depending on OS."""
    mock_DownloadFiles.return_value = '/tmp/tmpRandom/tomchop'
    mock_InitHttp.return_value.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    mock_Get.return_value = mock_grr_hosts.MOCK_FLOW
    self.grr_artifact_collector = grr_hosts.GRRArtifactCollector(
        self.test_state)
    self.grr_artifact_collector.SetUp(
        hostnames='C.0000000000000002',  # A windows host
        artifacts='RandomArtifact',
        extra_artifacts='AnotherArtifact',
        use_raw_filesystem_access=False,
        reason='Random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        max_file_size=1234,
        approvers='approver1,approver2',
        verify=False,
        skip_offline_clients=False
    )

    self.grr_artifact_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_artifact_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_artifact_collector.Process(c)
    self.grr_artifact_collector.PostProcess()

    kwargs = mock_ArtifactCollectorFlowArgs.call_args[1]
    # Raw access for Windows
    self.assertTrue(kwargs['use_raw_filesystem_access'])

  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch('grr_api_client.flow.FlowRef.Get')
  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('grr_response_proto.flows_pb2.ArtifactCollectorFlowArgs')
  def testProcessLinuxArtifacts(self,
                                   mock_ArtifactCollectorFlowArgs,
                                   mock_DownloadFiles,
                                   mock_CreateFlow,
                                   mock_Get,
                                   mock_InitHttp):
    """Tests that artifacts are obtained in raw mode depending on OS."""
    mock_DownloadFiles.return_value = '/tmp/tmpRandom/tomchop'
    mock_InitHttp.return_value.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    mock_Get.return_value = mock_grr_hosts.MOCK_FLOW
    self.grr_artifact_collector = grr_hosts.GRRArtifactCollector(
        self.test_state)
    self.grr_artifact_collector.SetUp(
        hostnames='C.0000000000000001',  # A Linux host
        artifacts='RandomArtifact',
        extra_artifacts='AnotherArtifact',
        use_raw_filesystem_access=False,
        reason='Random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        max_file_size=1234,
        approvers='approver1,approver2',
        verify=False,
        skip_offline_clients=False
    )

    self.grr_artifact_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_artifact_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_artifact_collector.Process(c)
    self.grr_artifact_collector.PostProcess()

    kwargs = mock_ArtifactCollectorFlowArgs.call_args[1]
    # No raw access for Linux
    self.assertFalse(kwargs['use_raw_filesystem_access'])

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('grr_api_client.flow.FlowBase.Get')
  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  def testProcess(self, mock_CreateFlow, mock_Get, mock_DownloadFiles):
    """Tests that the module is setup properly."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    mock_DownloadFiles.return_value = '/tmp/tmpRandom/tomchop'
    mock_Get.return_value = mock_grr_hosts.MOCK_FLOW

    self.grr_artifact_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_artifact_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_artifact_collector.Process(c)
    self.grr_artifact_collector.PostProcess()

    # Flow ID is F:12345, Client ID is C.0000000000000001
    self.mock_grr_api.SearchClients.assert_any_call('C.0000000000000001')
    self.assertEqual(mock_CreateFlow.call_count, 1)
    self.assertEqual(mock_DownloadFiles.call_count, 1)
    mock_DownloadFiles.assert_called_with(
        mock_grr_hosts.MOCK_CLIENT_LIST[1], mock_grr_hosts.MOCK_FLOW.flow_id
    )
    results = self.test_state.GetContainers(containers.File)
    self.assertEqual(len(results), 1)
    result = results[0]
    self.assertEqual(result.name, 'tomchop')
    self.assertEqual(result.path, '/tmp/tmpRandom/tomchop')

  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._FindClients')
  def testProcessFromContainers(self,
                                mock_FindClients,
                                unused_LaunchFlow,
                                unused_DownloadFiles,
                                unused_AwaitFlow,
                                mock_InitHttp):
    """Tests that processing works when only containers are passed."""
    mock_InitHttp.return_value = self.mock_grr_api
    self.grr_artifact_collector = grr_hosts.GRRArtifactCollector(
        self.test_state)
    self.grr_artifact_collector.SetUp(
        hostnames='',
        artifacts='RandomArtifact',
        extra_artifacts='AnotherArtifact',
        use_raw_filesystem_access=False,
        reason='Random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        approvers='approver1,approver2',
        verify=False,
        skip_offline_clients=False,
        max_file_size=1234,
    )
    self.test_state.StoreContainer(containers.Host(hostname='container.host'))

    self.grr_artifact_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_artifact_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_artifact_collector.Process(c)
    self.grr_artifact_collector.PostProcess()

    mock_FindClients.assert_called_with(['container.host'])


class GRRFileCollectorTest(unittest.TestCase):
  """Tests for the GRR file collector."""

  # For pytype
  grr_file_collector: grr_hosts.GRRFileCollector
  mock_grr_api: mock.Mock

  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp):
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.test_state = state.DFTimewolfState(config.Config)
    self.test_state.StoreContainer(containers.FSPath(path='/etc/hosts'))
    self.grr_file_collector = grr_hosts.GRRFileCollector(self.test_state)
    self.grr_file_collector.SetUp(
        hostnames='C.0000000000000001',
        files='/etc/passwd',
        use_raw_filesystem_access=False,
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        max_file_size='1234',
        approvers='approver1,approver2',
        skip_offline_clients=False,
        action='stat',
    )

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    # pytype: disable=attribute-error
    actual_hosts = [h.hostname for h in \
        self.grr_file_collector.state.GetContainers(
            self.grr_file_collector.GetThreadOnContainerType())]
    # pytype: enable=attribute-error

    self.assertIsNotNone(self.grr_file_collector)
    self.assertEqual(['C.0000000000000001'], actual_hosts)
    self.assertEqual(
        self.grr_file_collector.files, ['/etc/passwd'])

  def testPreProcess(self):
    """Tests the preprocess method."""
    self.grr_file_collector.PreProcess()
    self.assertEqual(
        self.grr_file_collector.files, ['/etc/passwd', '/etc/hosts'])

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  def testProcess(self, mock_LaunchFlow, mock_DownloadFiles, _):
    """Tests that processing launches appropriate flows."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_DownloadFiles.return_value = '/tmp/something'

    self.grr_file_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_file_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_file_collector.Process(c)
    self.grr_file_collector.PostProcess()

    mock_LaunchFlow.assert_called_with(
        mock_grr_hosts.MOCK_CLIENT_RECENT,
        'FileFinder',
        flows_pb2.FileFinderArgs(
            paths=['/etc/passwd', '/etc/hosts'],
            pathtype=jobs_pb2.PathSpec.OS,
            action=flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.STAT,
                download=flows_pb2.FileFinderDownloadActionOptions(
                    max_size=1234)
            )
        )
    )
    results = self.test_state.GetContainers(containers.File)
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].name, 'tomchop')
    self.assertEqual(results[0].path, '/tmp/something')

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow')
  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  def testWindowsProcess(self,
                         mock_LaunchFlow,
                         mock_DownloadFiles,
                         mock_InitHttp,
                         unused_await):
    """Tests that processing launches appropriate flows."""
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.mock_grr_api.SearchClients.return_value = \
        [mock_grr_hosts.MOCK_WINDOWS_CLIENT]
    mock_DownloadFiles.return_value = '/tmp/something'

    self.test_state.store = {}
    self.test_state.StoreContainer(containers.FSPath(path='/etc/hosts'))
    self.grr_file_collector = grr_hosts.GRRFileCollector(self.test_state)

    self.grr_file_collector.SetUp(
        hostnames='C.0000000000000002',
        files='/etc/passwd',
        use_raw_filesystem_access=False,
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        max_file_size='1234',
        approvers='approver1,approver2',
        skip_offline_clients=False,
        action='stat',
    )


    self.grr_file_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_file_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_file_collector.Process(c)
    self.grr_file_collector.PostProcess()

    mock_LaunchFlow.assert_called_with(
        mock_grr_hosts.MOCK_WINDOWS_CLIENT,
        'FileFinder',
        flows_pb2.FileFinderArgs(
            paths=['/etc/passwd', '/etc/hosts'],
            pathtype=jobs_pb2.PathSpec.NTFS,
            action=flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.STAT,
                download=flows_pb2.FileFinderDownloadActionOptions(
                    max_size=1234)
            )
        )
    )
    results = self.test_state.GetContainers(containers.File)
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].name, 'tomchop')
    self.assertEqual(results[0].path, '/tmp/something')

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._FindClients')
  def testProcessFromContainers(self,
                                mock_FindClients,
                                mock_InitHttp,
                                unused_LaunchFlow,
                                unused_DownloadFiles,
                                unused_AwaitFlow
                                ):
    """Tests that processing works when only containers are passed."""
    mock_InitHttp.return_value = self.mock_grr_api
    self.grr_file_collector = grr_hosts.GRRFileCollector(
        self.test_state)
    self.grr_file_collector.SetUp(
        hostnames='',
        files='/etc/passwd',
        use_raw_filesystem_access=False,
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        max_file_size='1234',
        approvers='approver1,approver2',
        skip_offline_clients=False,
        action='stat',
    )
    self.test_state.StoreContainer(containers.Host(hostname='container.host'))

    self.grr_file_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_file_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_file_collector.Process(c)
    self.grr_file_collector.PostProcess()

    mock_FindClients.assert_called_with(['container.host'])


class GRRFlowCollectorTest(unittest.TestCase):
  """Tests for the GRR flow collector."""

  # For pytype
  grr_flow_collector: grr_hosts.GRRFlowCollector
  mock_grr_api: mock.Mock
  test_state: state.DFTimewolfState

  @mock.patch('grr_api_client.client.Client.ListFlows')
  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp, mock_list_flows):
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_list_flows.return_value = [mock_grr_hosts.flow_pb_terminated]
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_flow_collector = grr_hosts.GRRFlowCollector(self.test_state)
    self.grr_flow_collector.SetUp(
        hostnames='C.0000000000000001',
        flow_ids='F:12345',
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        skip_offline_clients=False,
    )

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow')
  def testProcess(self, _, mock_DownloadFiles):
    """Tests that the collector can be initialized."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_DownloadFiles.return_value = '/tmp/something'

    self.grr_flow_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_flow_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_flow_collector.Process(c)
    self.grr_flow_collector.PostProcess()

    mock_DownloadFiles.assert_called_once_with(
        mock_grr_hosts.MOCK_CLIENT_RECENT, 'F:12345')
    results = self.test_state.GetContainers(containers.File)
    self.assertEqual(len(results), 1)
    result = results[0]
    self.assertEqual(result.name, 'tomchop')
    self.assertEqual(result.path, '/tmp/something')

  @mock.patch('grr_api_client.client.Client.ListFlows')
  @mock.patch('grr_api_client.api.InitHttp')
  def testSetUpMissingFlows(self, mock_InitHttp, mock_list_flows):
    """Tests missing flows are correctly identified."""
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_list_flows.return_value = [mock_grr_hosts.flow_pb_terminated]

    grr_flow_collector = grr_hosts.GRRFlowCollector(self.test_state)

    with self.assertLogs(grr_flow_collector.logger) as lc:
      grr_flow_collector.SetUp(
          hostnames='C.0000000000000001',
          flow_ids='F:12345,F:23456,F:34567',
          reason='random reason',
          grr_server_url='http://fake/endpoint',
          grr_username='admin',
          grr_password='admin',
          approvers='approver1,approver2',
          skip_offline_clients=False,
      )

      log_messages = [record.getMessage() for record in lc.records]
      # pylint: disable=line-too-long
      self.assertIn('The following flows were not found: F:23456, F:34567', log_messages)
      self.assertIn('Did you specify a child flow instead of a parent?', log_messages)
      # pylint: enable=line-too-long

  @mock.patch('grr_api_client.client.Client.ListFlows')
  @mock.patch('grr_api_client.api.InitHttp')
  def testPreProcessNoFlows(self, mock_InitHttp, mock_list_flows):
    """Tests that if no flows are found, an error is thrown."""
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_list_flows.return_value = [mock_grr_hosts.flow_pb_terminated]

    grr_flow_collector = grr_hosts.GRRFlowCollector(self.test_state)
    grr_flow_collector.SetUp(
        hostnames='C.0000000000000001',
        flow_ids='F:12345',
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        skip_offline_clients=False,
    )

    # Clear the containers to test correct failure on no containers being found.
    self.test_state.GetContainers(containers.GrrFlow, True)

    with self.assertRaises(errors.DFTimewolfError) as error:
      grr_flow_collector.PreProcess()
    self.assertEqual('No flows found for collection.', error.exception.message)
    self.assertEqual(len(self.test_state.errors), 1)

  @mock.patch('grr_api_client.client.Client.ListFlows')
  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow')
  def testProcessNoFlowData(self,
      _,
      mock_DLFiles,
      mock_InitHttp,
      mock_list_flows):
    """Tests Process when the flow is found but has no data collected."""
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_list_flows.return_value = [mock_grr_hosts.flow_pb_terminated]
    mock_DLFiles.return_value = None

    grr_flow_collector = grr_hosts.GRRFlowCollector(self.test_state)

    with self.assertLogs(grr_flow_collector.logger) as lc:
      grr_flow_collector.SetUp(
          hostnames='C.0000000000000001',
          flow_ids='F:12345',
          reason='random reason',
          grr_server_url='http://fake/endpoint',
          grr_username='admin',
          grr_password='admin',
          approvers='approver1,approver2',
          skip_offline_clients=False,
      )
      self.grr_flow_collector.PreProcess()
      in_containers = self.test_state.GetContainers(
          self.grr_flow_collector.GetThreadOnContainerType())
      for c in in_containers:
        self.grr_flow_collector.Process(c)
      self.grr_flow_collector.PostProcess()

      log_messages = [record.getMessage() for record in lc.records]
      # pylint: disable=line-too-long
      self.assertIn('No flow data collected for C.0000000000000001:F:12345', log_messages)
      # pylint: enable=line-too-long


class GRRTimelineCollectorTest(unittest.TestCase):
  """Tests for the GRR flow collector."""

  # For pytype
  grr_timeline_collector: grr_hosts.GRRTimelineCollector
  mock_grr_api: mock.Mock
  test_state: state.DFTimewolfState

  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp):
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_timeline_collector = grr_hosts.GRRTimelineCollector(
        self.test_state)
    self.grr_timeline_collector.SetUp(
        hostnames='C.0000000000000001',
        root_path='/',
        reason='random reason',
        timeline_format='1',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        skip_offline_clients=False,
    )

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    # pytype: disable=attribute-error
    actual_hosts = [h.hostname for h in \
        self.grr_timeline_collector.state.GetContainers(
            self.grr_timeline_collector.GetThreadOnContainerType())]
    # pytype: enable=attribute-error

    self.assertIsNotNone(self.grr_timeline_collector)
    self.assertEqual(['C.0000000000000001'], actual_hosts)
    self.assertEqual(self.grr_timeline_collector.root_path, b'/')
    self.assertEqual(self.grr_timeline_collector._timeline_format, 1)

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.'
              'GRRTimelineCollector._DownloadTimeline')
  # mock grr_api_client.flow.FlowBase.GetCollectedTimeline instead once when it
  # becomes available in pypi
  @mock.patch('grr_api_client.flow.FlowBase.Get')
  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  def testProcess(self, mock_CreateFlow, mock_Get, mock_DownloadTimeline):
    """Tests that the collector can be initialized."""
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_DownloadTimeline.return_value = '/tmp/something'
    mock_Get.return_value = mock_grr_hosts.MOCK_FLOW

    self.grr_timeline_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_timeline_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_timeline_collector.Process(c)
    self.grr_timeline_collector.PostProcess()

    mock_DownloadTimeline.assert_called_once_with(
        mock_grr_hosts.MOCK_CLIENT_RECENT, 'F:12345')
    results = self.test_state.GetContainers(containers.File)
    self.assertEqual(len(results), 1)
    result = results[0]
    self.assertEqual(result.name, 'tomchop')
    self.assertEqual(result.path, '/tmp/something')

  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._FindClients')
  def testProcessFromContainers(self,
                                mock_FindClients,
                                unused_LaunchFlow,
                                unused_DownloadFiles,
                                unused_AwaitFlow,
                                mock_InitHttp):
    """Tests that processing works when only containers are passed."""
    mock_InitHttp.return_value = self.mock_grr_api
    self.grr_timeline_collector = grr_hosts.GRRTimelineCollector(
        self.test_state)
    self.grr_timeline_collector.SetUp(
        hostnames='',
        root_path='/',
        reason='random reason',
        timeline_format='1',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2',
        skip_offline_clients=False,
    )
    self.test_state.StoreContainer(containers.Host(hostname='container.host'))

    self.grr_timeline_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_timeline_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_timeline_collector.Process(c)
    self.grr_timeline_collector.PostProcess()

    mock_FindClients.assert_called_with(['container.host'])


class GRROsqueryCollectorTest(unittest.TestCase):
  """Tests for the GRR Osquery collector."""

  # For pytype
  grr_osquery_collector: grr_hosts.GRROsqueryCollector
  mock_grr_api: mock.Mock
  test_state: state.DFTimewolfState

  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp):
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.test_state = state.DFTimewolfState(config.Config)
    self.test_state.StoreContainer(
      containers.OsqueryQuery('SELECT * FROM processes'))
    self.grr_osquery_collector = grr_hosts.GRROsqueryCollector(
        self.test_state)
    self.grr_osquery_collector.SetUp(
        hostnames='C.0000000000000001',
        reason='Random reason',
        timeout_millis=300000,
        ignore_stderr_errors=False,
        directory='',
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        approvers='approver1,approver2',
        verify=False,
        skip_offline_clients=False
    )

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self.grr_osquery_collector)

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRROsqueryCollector.'
              '_DownloadResults')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  def testProcess(self, mock_LaunchFlow, mock_DownloadResults, _):
    """Tests that the module launches appropriate flows."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_DownloadResults.return_value = [pd.DataFrame([[1, 2]])]

    self.grr_osquery_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_osquery_collector.GetThreadOnContainerType())
    for container in in_containers:
      self.grr_osquery_collector.Process(container)
    self.grr_osquery_collector.PostProcess()

    mock_LaunchFlow.assert_called_with(
        mock_grr_hosts.MOCK_CLIENT_RECENT,
        'OsqueryFlow',
        osquery_pb2.OsqueryFlowArgs(
            query='SELECT * FROM processes',
            timeout_millis=300000,
            ignore_stderr_errors=False
        )
    )

    results = self.test_state.GetContainers(containers.OsqueryResult)
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].query, 'SELECT * FROM processes')
    self.assertEqual(results[0].name, None)
    self.assertEqual(results[0].description, None)
    self.assertEqual(results[0].hostname, 'C.0000000000000001')
    self.assertEqual(results[0].client_identifier, 'C.0000000000000001')
    self.assertEqual(results[0].flow_identifier, 'F:12345')
    

if __name__ == '__main__':
  unittest.main()
