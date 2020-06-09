#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR base collector."""

import unittest
import mock

from grr_api_client import errors as grr_errors

from dftimewolf.lib import state
from dftimewolf.lib.collectors import grr_base

from dftimewolf import config


ACCESS_FORBIDDEN_MAX = 3


class MockGRRObject(object):
  """Fake GRR object that will be used in the access forbidden wrapper test"""
  _access_forbidden_counter = 0
  CreateApproval = mock.MagicMock()

  hunt_id = "123"
  client_id = "321"

  # pylint: disable=unused-argument
  def ForbiddenFunction(self, random1, random2, random3=None, random4=None):
    """Will raise a grr_errors.AccessForbiddenError three times, and return."""
    while ACCESS_FORBIDDEN_MAX > self._access_forbidden_counter:
      self._access_forbidden_counter += 1
      raise grr_errors.AccessForbiddenError
    return 4


class GRRBaseModuleTest(unittest.TestCase):
  """Tests for the GRR base collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    grr_base_module = grr_base.GRRBaseModule(test_state)
    self.assertIsNotNone(grr_base_module)

  @mock.patch('tempfile.mkdtemp')
  @mock.patch('grr_api_client.api.InitHttp')
  def testSetup(self, mock_grr_inithttp, mock_mkdtemp):
    """Tests that setup works"""
    test_state = state.DFTimewolfState(config.Config)
    grr_base_module = grr_base.GRRBaseModule(test_state)
    mock_mkdtemp.return_value = '/fake'
    grr_base_module.SetUp(
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin1',
        grr_password='admin2',
        approvers='approver1@example.com,approver2@example.com',
        verify=True
    )
    mock_grr_inithttp.assert_called_with(
        api_endpoint='http://fake/endpoint',
        auth=('admin1', 'admin2'),
        verify=True)
    self.assertEqual(grr_base_module.approvers,
                     ['approver1@example.com', 'approver2@example.com'])
    self.assertEqual(grr_base_module.output_path, '/fake')

  def testApprovalWrapper(self):
    """Tests that the approval wrapper works correctly."""
    test_state = state.DFTimewolfState(config.Config)
    grr_base_module = grr_base.GRRBaseModule(test_state)
    grr_base_module.SetUp(
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin1',
        grr_password='admin2',
        approvers='approver1@example.com,approver2@example.com',
        verify=True
    )
    # pylint: disable=protected-access
    grr_base_module._CHECK_APPROVAL_INTERVAL_SEC = 0
    mock_grr_object = MockGRRObject()
    mock_forbidden_function = mock.Mock(
        wraps=mock_grr_object.ForbiddenFunction)
    result = grr_base_module._WrapGRRRequestWithApproval(
        mock_grr_object,
        mock_forbidden_function,
        'random1',
        'random2',
        random3=4,
        random4=4)

    # Final result.
    self.assertEqual(result, 4)
    mock_forbidden_function.assert_called_with(
        'random1', 'random2', random3=4, random4=4)
    # Our forbidden function should be called 4 times, the last one succeeeding.
    self.assertEqual(mock_forbidden_function.call_count, 4)
    mock_grr_object.CreateApproval.assert_called_with(
        reason='random reason',
        notified_users=['approver1@example.com', 'approver2@example.com'])

  def testNoApproversErrorsOut(self):
    """Tests that an error is generated if no approvers are specified.

    This should only error on unauthorized objects, which is how our mock
    behaves.
    """
    test_state = state.DFTimewolfState(config.Config)
    grr_base_module = grr_base.GRRBaseModule(test_state)
    grr_base_module.SetUp(
        reason='random',
        grr_server_url='http://fake/url',
        grr_username='admin1',
        grr_password='admin2',
        approvers='',
        verify=True
    )
    # pylint: disable=protected-access
    grr_base_module._CHECK_APPROVAL_INTERVAL_SEC = 0
    mock_grr_object = MockGRRObject()
    mock_forbidden_function = mock.Mock(
        wraps=mock_grr_object.ForbiddenFunction)
    result = grr_base_module._WrapGRRRequestWithApproval(
        mock_grr_object,
        mock_forbidden_function,
        'random1',
        'random2',
        random3=4,
        random4=4)
    self.assertIsNone(result)
    # Only one error message is generateds
    self.assertEqual(len(test_state.errors), 1)
    # Correct error message is generated
    self.assertIn('no approvers specified', test_state.errors[0][0])
    self.assertTrue(test_state.errors[0][1])  # critical=True

if __name__ == '__main__':
  unittest.main()
