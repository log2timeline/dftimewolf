#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR base collector."""

from __future__ import unicode_literals

import unittest
import mock

from dftimewolf.lib import state
from dftimewolf.lib.collectors import grr_base


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
    self.assertEqual(grr_base_module.approvers, ['approver1@google.com', 'approver2@google.com'])
    self.assertEqual(grr_base_module.output_path, '/tmp/fake')





if __name__ == '__main__':
  unittest.main()
