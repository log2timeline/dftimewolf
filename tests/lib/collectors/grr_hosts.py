#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR host collectors."""

from __future__ import unicode_literals

import unittest
import mock

from grr_response_proto import flows_pb2

from dftimewolf.lib import state
from dftimewolf.lib.collectors import grr_hosts
from tests.lib.collectors.test_data import mock_grr_hosts


class GRRFlowTests(unittest.TestCase):
  """Tests for the GRRFlow base class."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    base_grr_flow_collector = grr_hosts.GRRFlow(test_state)
    self.assertIsNotNone(base_grr_flow_collector)

  @mock.patch('grr_api_client.api.GrrApi.SearchClients')
  def testGetClientByHostname(self, mock_SearchClients):
    """Tests that GetClientByHostname fetches the most recent GRR client."""
    mock_SearchClients.return_value = mock_grr_hosts.MOCK_CLIENT_LIST
    test_state = state.DFTimewolfState()
    base_grr_flow_collector = grr_hosts.GRRFlow(test_state)
    base_grr_flow_collector.setup(
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin1',
        grr_password='admin2',
        approvers='approver1@example.com,approver2@example.com',
        verify=True
    )
    # pylint: disable=protected-access
    client = base_grr_flow_collector._get_client_by_hostname('tomchop')
    mock_SearchClients.assert_called_with('tomchop')
    self.assertEqual(
        client.data.client_id, mock_grr_hosts.MOCK_CLIENT_RECENT.data.client_id)

  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  def testLaunchFlow(self, mock_CreateFlow):
    """Tests that CreateFlow is correctly called."""
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    test_state = state.DFTimewolfState()
    base_grr_flow_collector = grr_hosts.GRRFlow(test_state)
    base_grr_flow_collector.setup(
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin1',
        grr_password='admin2',
        approvers='approver1@example.com,approver2@example.com',
        verify=True
    )
    # pylint: disable=protected-access
    flow_id = base_grr_flow_collector._launch_flow(
        mock_grr_hosts.MOCK_CLIENT, "FlowName", "FlowArgs")
    self.assertEqual(flow_id, 'F:12345')
    mock_CreateFlow.assert_called_once_with(name="FlowName", args="FlowArgs")

  @mock.patch('grr_api_client.client.ClientBase.CreateFlow')
  def testLaunchFlowKeepalive(self, mock_CreateFlow):
    """Tests that keepalive flows are correctly created."""
    mock_CreateFlow.return_value = mock_grr_hosts.MOCK_FLOW
    test_state = state.DFTimewolfState()
    base_grr_flow_collector = grr_hosts.GRRFlow(test_state)
    base_grr_flow_collector.setup(
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin1',
        grr_password='admin2',
        approvers='approver1@example.com,approver2@example.com',
        verify=True
    )
    base_grr_flow_collector.keepalive = True
    # pylint: disable=protected-access
    flow_id = base_grr_flow_collector._launch_flow(
        mock_grr_hosts.MOCK_CLIENT, "FlowName", "FlowArgs")
    self.assertEqual(flow_id, 'F:12345')
    self.assertEqual(mock_CreateFlow.call_count, 2)
    self.assertEqual(
        mock_CreateFlow.call_args,
        ((), {'name': 'KeepAlive', 'args': flows_pb2.KeepAliveArgs()}))

class GRRArtifactCollectorTest(unittest.TestCase):
  """Tests for the GRR artifact collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_artifact_collector = grr_hosts.GRRArtifactCollector(test_state)
    self.assertIsNotNone(grr_artifact_collector)


class GRRFileCollectorTest(unittest.TestCase):
  """Tests for the GRR file collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_file_collector = grr_hosts.GRRFileCollector(test_state)
    self.assertIsNotNone(grr_file_collector)


class GRRFlowCollector(unittest.TestCase):
  """Tests for the GRR flow collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_flow_collector = grr_hosts.GRRFlowCollector(test_state)
    self.assertIsNotNone(grr_flow_collector)


if __name__ == '__main__':
  unittest.main()
