#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the SSH multiplexer preflight."""

import unittest
import mock

from dftimewolf.lib.preflights import ssh_multiplexer
from tests.lib import modules_test_base


class SSHMultiplexer(modules_test_base.ModuleTestBase):
  """Tests for the SSH multiplexer preflight."""

  def setUp(self):
    with mock.patch.object(ssh_multiplexer, 'uuid') as mock_uuid:
      mock_uuid.uuid4.return_value = '8f473cb2-db6d-4ce5-8d81-ed15d4f38fc5'
      self._InitModule(ssh_multiplexer.SSHMultiplexer)
    super().setUp()

  @mock.patch('subprocess.call')
  def testProcess(self, mock_call):
    """Tests the SSH CLI has the expected parameters."""
    mock_call.return_value = 0

    self._module.SetUp('fakehost', 'fakeuser', None, ['-o', "ProxyCommand='test'"])
    self._ProcessModule()

    mock_call.assert_called_with([
      'ssh', '-q', '-l', 'fakeuser',
      '-o', 'ControlMaster=auto',
      '-o', 'ControlPersist=yes',
      '-o', 'ControlPath=~/.ssh/ctrl-dftw-8f473cb2-db6d-4ce5-8d81-ed15d4f38fc5',
      '-o', "ProxyCommand='test'",
      'fakehost', 'true',
    ])

  @mock.patch('subprocess.call')
  def testCleanup(self, mock_call):
    """Tests that the SSH CLI is called with the expected arguments."""
    mock_call.return_value = 0

    self._module.SetUp('fakehost', 'fakeuser', None, [])
    self._module.CleanUp()

    mock_call.assert_called_with([
      'ssh', '-O', 'exit', '-o',
      'ControlPath=~/.ssh/ctrl-dftw-8f473cb2-db6d-4ce5-8d81-ed15d4f38fc5',
      'fakehost'
    ])


if __name__ == '__main__':
  unittest.main()
