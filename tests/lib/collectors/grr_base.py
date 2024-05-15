#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR base collector."""

import unittest
import logging
import mock

from grr_api_client import errors as grr_errors

from dftimewolf.lib import errors
from dftimewolf.lib.collectors import grr_base


ACCESS_FORBIDDEN_MAX = 3


class MockGRRObject(object):
  """Fake GRR object that will be used in the access forbidden wrapper test"""
  _access_forbidden_counter = 0
  CreateApproval = mock.MagicMock()
  ClientApproval = mock.MagicMock()
  ClientApproval.client_id = "abcd"
  ClientApproval.approval_id = "dcba"
  ClientApproval.username = "nobody"
  CreateApproval.return_value = ClientApproval

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
    grr_base_module = grr_base.GRRBaseModule()
    self.assertIsNotNone(grr_base_module)

  @mock.patch('tempfile.mkdtemp')
  @mock.patch('grr_api_client.api.InitHttp')
  def testSetup(self, mock_grr_inithttp, mock_mkdtemp):
    """Tests that setup works"""
    grr_base_module = grr_base.GRRBaseModule()
    mock_publish_message = mock.MagicMock()
    mock_mkdtemp.return_value = '/fake'
    grr_base_module.GrrSetUp(
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin1',
        grr_password='admin2',
        message_callback=mock_publish_message,
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

  @mock.patch('grr_api_client.api.InitHttp')
  def testApprovalWrapper(self, _):
    """Tests that the approval wrapper works correctly."""
    mock_publish_message = mock.MagicMock()
    grr_base_module = grr_base.GRRBaseModule()
    grr_base_module.GrrSetUp(
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin1',
        grr_password='admin2',
        message_callback=mock_publish_message,
        approvers='approver1@example.com,approver2@example.com',
        verify=True
    )
    # pylint: disable=protected-access,invalid-name
    grr_base_module._CHECK_APPROVAL_INTERVAL_SEC = 0
    mock_grr_object = MockGRRObject()
    mock_forbidden_function = mock.Mock(
        wraps=mock_grr_object.ForbiddenFunction)
    result = grr_base_module._WrapGRRRequestWithApproval(
        mock_grr_object,
        mock_forbidden_function,
        logging.getLogger('GRRBaseModuleTest'),
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

    mock_publish_message.assert_has_calls([
      # pylint: disable=line-too-long
      mock.call('Approval needed at: http://fake/endpoint/v2/clients/abcd/users/nobody/approvals/dcba', False)
      # pylint: enable=line-too-long
    ])
    self.assertEqual(mock_publish_message.call_count, 1)

  @mock.patch('grr_api_client.api.InitHttp')
  def testNoApproversErrorsOut(self, _):
    """Tests that an error is generated if no approvers are specified.

    This should only error on unauthorized objects, which is how our mock
    behaves.
    """
    mock_publish_message = mock.MagicMock()
    grr_base_module = grr_base.GRRBaseModule()
    grr_base_module.GrrSetUp(
        reason='random',
        grr_server_url='http://fake/url',
        grr_username='admin1',
        grr_password='admin2',
        message_callback=mock_publish_message,
        approvers='',
        verify=True
    )

    # pylint: disable=protected-access
    grr_base_module._CHECK_APPROVAL_INTERVAL_SEC = 0
    mock_grr_object = MockGRRObject()
    mock_forbidden_function = mock.Mock(
        wraps=mock_grr_object.ForbiddenFunction)
    with self.assertRaises(errors.DFTimewolfError) as error:
      grr_base_module._WrapGRRRequestWithApproval(
          mock_grr_object,
          mock_forbidden_function,
          logging.getLogger('GRRBaseModuleTest'),
          'random1',
          'random2',
          random3=4,
          random4=4)
    self.assertEqual('GRR needs approval but no approvers specified '
                     '(hint: use --approvers)', error.exception.message)
    self.assertTrue(error.exception.critical)

if __name__ == '__main__':
  unittest.main()
