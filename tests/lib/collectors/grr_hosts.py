#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR host collectors."""

import unittest

import os
import tempfile
from typing import IO

import mock

import pandas as pd
from grr_api_client import errors as grr_errors
from grr_api_client import client
from grr_response_proto.api import client_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import osquery_pb2
from grr_response_proto import timeline_pb2
from google.protobuf import text_format
from tests.lib.collectors.test_data import mock_grr_hosts

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib import errors
from dftimewolf.lib.collectors import grr_hosts
from dftimewolf.lib.containers import containers


def _MOCK_WRITE_TO_STREAM(out: IO[bytes]):
  for _ in range(1024):
    out.write(b'\0')


def _MOCK_WRITE_TO_FILE(path: str):
  with open(path, 'wb') as fp:
    for _ in range(1024):
      fp.write(b'\0')


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
    # pylint: disable=invalid-name
    self.grr_flow_module._CHECK_FLOW_INTERVAL_SEC = 1

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self.grr_flow_module)

  def testGetClientBySelector(self):
    """Tests that GetClientBySelector fetches the most recent GRR client."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    client_handle = self.grr_flow_module._GetClientBySelector(
        'C.0000000000000001')
    self.mock_grr_api.SearchClients.assert_called_with('C.0000000000000001')
    self.assertEqual(client_handle.data.client_id, 'C.0000000000000001')

  def testGetClientByUsername(self):
    """Tests that GetClientBySelector fetches the correct GRR client."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    client_handle = self.grr_flow_module._GetClientBySelector(
        'tomchop_username2')
    self.mock_grr_api.SearchClients.assert_called_with('tomchop_username2')
    self.assertEqual(client_handle.data.client_id, 'C.0000000000000001')

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

  @mock.patch('grr_api_client.flow.FlowBase.Get')
  def testDownloadFilesForFlow(self, mock_Get):
    """Test if results are downloaded to the correct directories."""
    mock_Get.return_value.data.name = 'ClientFileFinder'
    mock_Get.return_value.ListResults.return_value = (
        mock_grr_hosts.MOCK_CFF_RESULTS)

    mock_client = client.Client(
        data=text_format.Parse(mock_grr_hosts.client_proto1,
                               client_pb2.ApiClient()),
        context=True)
    mock_client.File = mock.MagicMock()
    mock_client.File.return_value.GetBlob.return_value.WriteToStream = (
        _MOCK_WRITE_TO_STREAM)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as local_path:
      self.grr_flow_module.output_path = local_path

      self.grr_flow_module._DownloadFiles(mock_client, 'F:12345')

      self.assertTrue(
          os.path.exists(
              os.path.join(local_path, mock_client.data.os_info.fqdn.lower(),
                           'F:12345', 'fs', 'os', 'directory', 'file')))

  @mock.patch("os.remove")
  @mock.patch('os.makedirs')
  @mock.patch("zipfile.ZipFile")
  @mock.patch('grr_api_client.flow.FlowBase.GetFilesArchive')
  @mock.patch('grr_api_client.flow.FlowBase.Get')
  def testDownloadTimelineBodyForFlow(
    self,
    mock_Get,
    mock_GetFilesArchive,
    mock_ZipFile,
    mock_makedirs,
    unused_mock_remove,
  ):
    """Tests if timeline results are downloaded in the correct directories."""
    # Change output_path to something constant so we can easily assert
    # if calls were done correctly.
    self.grr_flow_module.output_path = "/tmp/random"
    mock_Get.return_value.data.name = 'TimelineFlow'
    mock_Get.return_value.GetCollectedTimelineBody = mock.MagicMock()

    return_value = self.grr_flow_module._DownloadFiles(
        mock_grr_hosts.MOCK_CLIENT, 'F:12345')
    self.assertEqual(return_value, '/tmp/random/tomchop/F:12345')
    mock_Get.return_value.GetCollectedTimelineBody.assert_called_once()
    mock_GetFilesArchive.assert_not_called()
    mock_ZipFile.assert_not_called()
    mock_makedirs.assert_called_once_with(
      "/tmp/random/tomchop/F:12345", exist_ok=True
    )

  @mock.patch("builtins.open")
  @mock.patch('grr_api_client.flow.FlowBase.ListResults')
  def testDownloadOsqueryForFlow(self, mock_ListResults, unused_mock_open):
    """Tests if Osquery results are downloaded in the correct directories."""
    mock_flowresult = mock.MagicMock()
    mock_flowresult.payload = osquery_pb2.OsqueryResult()
    mock_ListResults.return_value = [
        mock_flowresult
    ]
    return_value = self.grr_flow_module._DownloadOsquery(
        mock_grr_hosts.MOCK_CLIENT, 'F:12345', '/tmp/random')
    self.assertEqual(return_value, '/tmp/random/tomchop.F:12345.csv')

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
        max_file_size='1234',
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
        self.grr_artifact_collector.GetContainers(
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
        max_file_size='1234',
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
        max_file_size='1234',
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
    self.assertFalse(kwargs["use_raw_filesystem_access"])

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
        max_file_size='1234',
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
    in_containers = self.grr_artifact_collector.GetContainers(
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
    results = self.grr_artifact_collector.GetContainers(containers.File)
    self.assertEqual(len(results), 1)
    result = results[0]
    self.assertEqual(result.name, 'tomchop')
    self.assertEqual(result.path, '/tmp/tmpRandom/tomchop')

  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow")
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._FindClients')
  def testProcessFromHostContainers(
    self,
    mock_FindClients,
    unused_LaunchFlow,
    unused_DownloadFiles,
    unused_AwaitFlow,
    mock_InitHttp,
  ):
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
        max_file_size='1234',
    )
    self.grr_artifact_collector.StoreContainer(
        containers.Host(hostname='container.host'))

    self.grr_artifact_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
        self.grr_artifact_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_artifact_collector.Process(c)
    self.grr_artifact_collector.PostProcess()

    mock_FindClients.assert_called_with(['container.host'])

  @mock.patch("grr_api_client.api.InitHttp")
  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow")
  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles")
  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow")
  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._FindClients")
  def testProcessFromArtifactContainers(
    self,
    mock_FindClients,
    mock_LaunchFlow,
    mock_DownloadFiles,
    unused_AwaitFlow,
    mock_InitHttp,
  ):
    """Tests that processing works when only containers are passed."""
    mock_FindClients.return_value = [mock_grr_hosts.MOCK_CLIENT]
    mock_InitHttp.return_value = self.mock_grr_api
    self.grr_artifact_collector = grr_hosts.GRRArtifactCollector(
      self.test_state
    )
    mock_DownloadFiles.return_value = "/tmp/tmpRandom/tomchop"

    self.grr_artifact_collector.SetUp(
      hostnames="C.0000000000000000",
      artifacts=None,
      extra_artifacts="AnotherArtifact",
      use_raw_filesystem_access=False,
      reason="Random reason",
      grr_server_url="http://fake/endpoint",
      grr_username="user",
      grr_password="password",
      approvers="approver1,approver2",
      verify=False,
      skip_offline_clients=False,
      max_file_size="1234",
    )
    self.grr_artifact_collector.StoreContainer(
      containers.GRRArtifact(name="ForensicArtifact1")
    )
    self.grr_artifact_collector.StoreContainer(
      containers.GRRArtifact(name="ForensicArtifact2")
    )

    self.grr_artifact_collector.PreProcess()
    in_containers = self.test_state.GetContainers(
      self.grr_artifact_collector.GetThreadOnContainerType()
    )
    for c in in_containers:
      self.grr_artifact_collector.Process(c)
    self.grr_artifact_collector.PostProcess()

    actual_flow_proto = mock_LaunchFlow.call_args_list[0][0][2]
    self.assertListEqual(
      sorted(actual_flow_proto.artifact_list),
      [
        "AnotherArtifact",
        "ForensicArtifact1",
        "ForensicArtifact2",
      ],
    )


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
    self.grr_file_collector = grr_hosts.GRRFileCollector(self.test_state)
    self.grr_file_collector.StoreContainer(containers.FSPath(path='/etc/hosts'))
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
        self.grr_file_collector.GetContainers(
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

  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow")
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  def testProcess(self, mock_LaunchFlow, mock_DownloadFiles, _):
    """Tests that processing launches appropriate flows."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_DownloadFiles.return_value = '/tmp/something'

    self.grr_file_collector.PreProcess()
    in_containers = self.grr_file_collector.GetContainers(
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
    results = self.grr_file_collector.GetContainers(containers.File)
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].name, 'tomchop')
    self.assertEqual(results[0].path, '/tmp/something')

  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow")
  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  def testWindowsProcess(
    self, mock_LaunchFlow, mock_DownloadFiles, mock_InitHttp, unused_AwaitFlow
  ):
    """Tests that processing launches appropriate flows."""
    self.mock_grr_api = mock.Mock()
    mock_InitHttp.return_value = self.mock_grr_api
    self.mock_grr_api.SearchClients.return_value = \
        [mock_grr_hosts.MOCK_WINDOWS_CLIENT]
    mock_DownloadFiles.return_value = '/tmp/something'

    self.test_state.store = {}
    self.grr_file_collector = grr_hosts.GRRFileCollector(self.test_state)
    self.grr_file_collector.StoreContainer(containers.FSPath(path='/etc/hosts'))

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
    results = self.grr_file_collector.GetContainers(containers.File)
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].name, 'tomchop')
    self.assertEqual(results[0].path, '/tmp/something')

  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow")
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
    self.grr_file_collector.StoreContainer(
        containers.Host(hostname='container.host'))

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

  @mock.patch('grr_api_client.flow.FlowBase.Get')
  @mock.patch('grr_api_client.client.Client.ListFlows')
  @mock.patch('grr_api_client.api.InitHttp')
  def setUp(self, mock_InitHttp, mock_list_flows, unused_mock_flow_get):
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
  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow")
  def testProcess(self, _, mock_DownloadFiles):
    """Tests that the collector can be initialized."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_DownloadFiles.return_value = '/tmp/something'

    self.grr_flow_collector.PreProcess()
    in_containers = self.grr_flow_collector.GetContainers(
        self.grr_flow_collector.GetThreadOnContainerType())
    for c in in_containers:
      self.grr_flow_collector.Process(c)
    self.grr_flow_collector.PostProcess()

    mock_DownloadFiles.assert_called_once_with(
        mock_grr_hosts.MOCK_CLIENT_RECENT, 'F:12345')
    results = self.grr_flow_collector.GetContainers(containers.File)
    self.assertEqual(len(results), 1)
    result = results[0]
    self.assertEqual(result.name, 'tomchop')
    self.assertEqual(result.path, '/tmp/something')

  @mock.patch('grr_api_client.flow.FlowBase.Get')
  @mock.patch('grr_api_client.client.Client.ListFlows')
  @mock.patch('grr_api_client.api.InitHttp')
  def testPreProcessNoFlows(
    self, mock_InitHttp, mock_list_flows, unused_mock_flow_get):
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
    self.grr_flow_collector.GetContainers(containers.GrrFlow, True)

    with self.assertRaises(errors.DFTimewolfError) as error:
      grr_flow_collector.PreProcess()
    self.assertEqual('No flows found for collection.', error.exception.message)
    self.assertEqual(len(self.test_state.errors), 1)

  @mock.patch('grr_api_client.flow.FlowBase.Get')
  @mock.patch('grr_api_client.client.Client.ListFlows')
  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow")
  def testProcessNoFlowData(
    self, _, mock_DLFiles, mock_InitHttp, mock_list_flows, unused_mock_flow_get
  ):
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
      in_containers = self.grr_flow_collector.GetContainers(
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
        self.grr_timeline_collector.GetContainers(
            self.grr_timeline_collector.GetThreadOnContainerType())]
    # pytype: enable=attribute-error

    self.assertIsNotNone(self.grr_timeline_collector)
    self.assertEqual(['C.0000000000000001'], actual_hosts)
    self.assertEqual(self.grr_timeline_collector.root_path, b'/')
    self.assertEqual(self.grr_timeline_collector._timeline_format, 1)

  def testProcess(self):
    """Tests the Process method of GRRTimelineCollector."""
    self.grr_timeline_collector._GetClientBySelector = mock.MagicMock()
    self.grr_timeline_collector._GetClientBySelector.return_value = (
        mock_grr_hosts.MOCK_CLIENT)

    with (
      mock.patch(
        "grr_api_client.client.ClientBase.CreateFlow"
      ) as mock_createflow,
      mock.patch(
        "grr_api_client.flow.FlowBase.GetCollectedTimelineBody"
      ) as mock_getcollectedtimeline,
      mock.patch("grr_api_client.flow.FlowBase.Get") as mock_get,
    ):
      mock_get.return_value = mock_grr_hosts.MOCK_FLOW
      mock_createflow.return_value.flow_id = "F:12345"
      mock_getcollectedtimeline.return_value.WriteToFile = _MOCK_WRITE_TO_FILE

      self.grr_timeline_collector.PreProcess()
      in_containers = self.grr_timeline_collector.GetContainers(
          self.grr_timeline_collector.GetThreadOnContainerType())
      for c in in_containers:
        self.grr_timeline_collector.Process(c) # pytype: disable=wrong-arg-types
      self.grr_timeline_collector.PostProcess()

      mock_createflow.assert_called_once_with(
        name="TimelineFlow", args=timeline_pb2.TimelineArgs(root=b"/")
      )

      expected_output_path = os.path.join(
        self.grr_timeline_collector.output_path,
        f'{mock_createflow.return_value.flow_id}_timeline.body')

      self.assertTrue(os.path.exists(expected_output_path))

  @mock.patch('grr_api_client.api.InitHttp')
  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow")
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._DownloadFiles')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._FindClients')
  def testProcessFromContainers(
    self,
    mock_FindClients,
    unused_LaunchFlow,
    unused_DownloadFiles,
    unused_AwaitFlow,
    mock_InitHttp,
  ):
    """Tests that processing works when only containers are passed."""
    mock_InitHttp.return_value = self.mock_grr_api
    self.grr_timeline_collector = grr_hosts.GRRTimelineCollector(
        self.test_state)
    self.grr_timeline_collector.StoreContainer(
        containers.Host(hostname='container.host'))
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
    self.grr_osquery_collector = grr_hosts.GRROsqueryCollector(
        self.test_state)
    self.grr_osquery_collector.StoreContainer(
      containers.OsqueryQuery(
          'SELECT * FROM processes',
          configuration_path='/test/path',
          file_collection_columns=['path']))
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

  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow")
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRROsqueryCollector.'
              '_DownloadResults')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  def testProcess(self, mock_LaunchFlow, mock_DownloadResults, _):
    """Tests that the module launches appropriate flows."""
    self.mock_grr_api.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_DownloadResults.return_value = [pd.DataFrame([[1, 2]])]

    self.grr_osquery_collector.PreProcess()
    in_containers = self.grr_osquery_collector.GetContainers(
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
            ignore_stderr_errors=False,
            configuration_content='',
            configuration_path='/test/path',
            file_collection_columns=['path']
        )
    )

    results = self.grr_osquery_collector.GetContainers(containers.OsqueryResult)
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].query, 'SELECT * FROM processes')
    self.assertEqual(results[0].name, None)
    self.assertEqual(results[0].description, None)
    self.assertEqual(results[0].hostname, 'C.0000000000000001')
    self.assertEqual(results[0].client_identifier, 'C.0000000000000001')


class GRRYaraScannerTest(unittest.TestCase):
  """Tests for the GRR Yara scanner."""

  # For pytype
  grr_yara_scanner: grr_hosts.GRRYaraScanner
  mock_grr_api: mock.Mock
  test_state: state.DFTimewolfState

  def setUp(self):
    self.mock_grr_api = mock.Mock()
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_yara_scanner = grr_hosts.GRRYaraScanner(
        self.test_state)
    self.grr_yara_scanner.StoreContainer(
      containers.YaraRule(
        name="test_rule",
        rule_text=('rule test_rule { condition: true and '
                   'hash.sha256("") != "" }'))
    )

  @mock.patch('grr_api_client.api.InitHttp')
  def testInitialization(self, unused_mock_InitHttp):
    """Tests that the collector can be initialized."""
    self.grr_yara_scanner.SetUp(
        reason='Random reason',
        hostnames='C.0000000000000001',
        process_ignorelist='.*',
        cmdline_ignorelist=None,
        dump_process_on_match=False,
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        approvers='approver1,approver2',
        verify=False,
        skip_offline_clients=False
    )
    self.assertIsNotNone(self.grr_yara_scanner)

  @mock.patch('grr_api_client.api.InitHttp')
  def testInitializeBadRegex(self, unused_mock_InitHttp):
    """Tests that bad regexes get caught upon initialization."""
    with self.assertRaises(errors.DFTimewolfError) as error:
      self.grr_yara_scanner.SetUp(
          reason='Random reason',
          hostnames='C.0000000000000001',
          process_ignorelist='(((((((',
          cmdline_ignorelist=None,
          dump_process_on_match=False,
          grr_server_url='http://fake/endpoint',
          grr_username='user',
          grr_password='password',
          approvers='approver1,approver2',
          verify=False,
          skip_offline_clients=False
      )
    self.assertEqual(
        'Invalid regex for process_ignorelist: missing ), unterminated '
        'subpattern at position 15',
        error.exception.message)

  @mock.patch("dftimewolf.lib.collectors.grr_hosts.GRRFlow._AwaitFlow")
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRROsqueryCollector.'
              '_DownloadResults')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  @mock.patch('grr_api_client.flow.FlowBase.Get')
  @mock.patch('grr_api_client.api.InitHttp')
  def testProcess(
    self,
    mock_InitHttp,
    mock_Get,
    unused_mock_LaunchFlow,
    unused_mock_DownloadResults,
    unused_mock_AwaitFlow):
    """Tests that the module launches appropriate flows."""
    mock_InitHttp.return_value.SearchClients.return_value = \
        mock_grr_hosts.MOCK_CLIENT_LIST
    mock_payloads = [mock.Mock(payload=mock_grr_hosts.MOCK_YARASCAN_PAYLOAD)]
    mock_ListResults = mock.Mock()
    mock_ListResults.return_value = mock_payloads
    mock_Get.return_value.ListResults = mock_ListResults

    self.grr_yara_scanner.SetUp(
        reason='Random reason',
        hostnames='C.0000000000000001',
        process_ignorelist='.*',
        cmdline_ignorelist=None,
        dump_process_on_match=False,
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        approvers='approver1,approver2',
        verify=False,
        skip_offline_clients=False
    )

    self.grr_yara_scanner.PreProcess()
    in_containers = self.grr_yara_scanner.GetContainers(
        self.grr_yara_scanner.GetThreadOnContainerType())
    for container in in_containers:
      self.grr_yara_scanner.Process(container)
    self.grr_yara_scanner.PostProcess()

    df_containers = self.grr_yara_scanner.GetContainers(containers.DataFrame)
    self.assertEqual(len(df_containers), 1)
    df = df_containers[0].data_frame
    self.assertEqual(
      df.to_dict(orient='records'),
      [
        {
          'grr_client': 'C.0000000000000001',
          'grr_fqdn': 'tomchop',
          'pid': 12345,
          'process': 'C:\\temp\\bad.exe',
          'cmdline': 'C:\\temp\\bad.exe arg1 arg2',
          'username': 'tomchop',
          'cwd': 'C:\\temp',
          'rule_name': 'badstring',
          'string_matches': ['$badstring1', '$badstring2']
        },
        {
          'grr_client': 'C.0000000000000001',
          'grr_fqdn': 'tomchop',
          'pid': 12345,
          'process': 'C:\\temp\\bad.exe',
          'cmdline': 'C:\\temp\\bad.exe arg1 arg2',
          'username': 'tomchop',
          'cwd': 'C:\\temp',
          'rule_name': 'superbadstring',
          'string_matches': ['$superbadstring1', '$superbadstring2']
        }
      ]
    )

  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRROsqueryCollector.'
              '_DownloadResults')
  @mock.patch('dftimewolf.lib.collectors.grr_hosts.GRRFlow._LaunchFlow')
  @mock.patch('grr_api_client.flow.FlowBase.Get')
  @mock.patch('grr_api_client.api.InitHttp')
  def testPreProcess(
    self,
    unused_mock_InitHttp,
    unused_mock_Get,
    unused_mock_LaunchFlow,
    unused_mock_DownloadResults):
    """Tests that the prexes are appended to a Yara rule that uses modules."""
    self.grr_yara_scanner.SetUp(
        reason='Random reason',
        hostnames='C.0000000000000001',
        process_ignorelist='.*',
        cmdline_ignorelist=None,
        dump_process_on_match=False,
        grr_server_url='http://fake/endpoint',
        grr_username='user',
        grr_password='password',
        approvers='approver1,approver2',
        verify=False,
        skip_offline_clients=False
    )
    self.grr_yara_scanner.PreProcess()
    self.assertEqual(
      self.grr_yara_scanner.rule_text,
      'import "hash"\n\nrule test_rule { condition: true and'
      ' hash.sha256("") != "" }')


if __name__ == '__main__':
  unittest.main()
