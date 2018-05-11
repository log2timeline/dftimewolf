#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR base collector."""

from __future__ import unicode_literals

import unittest
import mock

from grr_api_client import errors as grr_errors

from dftimewolf.lib import state
from dftimewolf.lib.collectors import grr_base

ACCESS_FORBIDDEN_MAX = 3

class MockGRRObject(object):
  """Fake GRR object that will be used in the access forbidden wrapper test"""
  _access_forbidden_counter = 0
  CreateApproval = mock.MagicMock()

  hunt_id = "123"
  # pylint: disable=unused-argument
  def forbidden_function(self, random1, random2, random3=None, random4=None):
    """Will raise a grr_errors.AccessForbiddenError three times, and return."""
    while ACCESS_FORBIDDEN_MAX > self._access_forbidden_counter:
      self._access_forbidden_counter += 1
      raise grr_errors.AccessForbiddenError
    return 4

class GRRBaseModuleTest(unittest.TestCase):
  """Tests for the GRR base collector."""



  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_base_module = grr_base.GRRBaseModule(test_state)
    self.assertIsNotNone(grr_base_module)

  @mock.patch('tempfile.mkdtemp')
  @mock.patch('grr_api_client.api.InitHttp')
  def testSetup(self, mock_grr_inithttp, mock_mkdtemp):
    """Tests that setup works"""
    test_state = state.DFTimewolfState()
    grr_base_module = grr_base.GRRBaseModule(test_state)
    mock_mkdtemp.return_value = '/tmp/fake'
    grr_base_module.setup('random reason',
                          'http://fake/endpoint',
                          ('admin', 'admin'),
                          'approver1@google.com,approver2@google.com')
    mock_grr_inithttp.assert_called_with(
        api_endpoint='http://fake/endpoint', auth=('admin', 'admin'))
    self.assertEqual(grr_base_module.approvers,
                     ['approver1@google.com', 'approver2@google.com'])
    self.assertEqual(grr_base_module.output_path, '/tmp/fake')

  def testApprovalWrapper(self):
    """Tests that the approval wrapper works correctly."""
    test_state = state.DFTimewolfState()
    grr_base_module = grr_base.GRRBaseModule(test_state)
    grr_base_module.setup('random reason',
                          'http://fake/endpoint',
                          ('admin', 'admin'),
                          'approver1@google.com,approver2@google.com')
    # pylint: disable=protected-access
    grr_base_module._CHECK_APPROVAL_INTERVAL_SEC = 0
    mock_grr_object = MockGRRObject()
    mock_forbidden_function = mock.Mock(
        wraps=mock_grr_object.forbidden_function)
    result = grr_base_module._check_approval_wrapper(
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
        reason='random reason', notified_users=['approver1@google.com', 'approver2@google.com'])

 # test noapprovers returns none on check approval wrapper



if __name__ == '__main__':
  unittest.main()
