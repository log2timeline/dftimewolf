#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the SSH multiplexer preflight."""

import unittest
import mock

from dftimewolf.lib import state
from dftimewolf.lib.preflights import ssh_multiplexer

from dftimewolf import config


class SSHMultiplexer(unittest.TestCase):
  """Tests for the SSH multiplexer preflight."""

  def testInitialization(self):
    """Tests that the exporter can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    local_ssh_multiplexer = ssh_multiplexer.SSHMultiplexer(test_state)
    self.assertIsNotNone(local_ssh_multiplexer)

  @mock.patch('subprocess.call')
  def testProcess(self, mock_call):
    """Tests the SSH CLI has the expected parameters."""
    mock_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    ssh_multi = ssh_multiplexer.SSHMultiplexer(test_state)
    ssh_multi.SetUp('fakehost', 'fakeuser', None, ['-o', "ProxyCommand='test'"])
    ssh_multi.Process()

    mock_call.assert_called_with([
      'ssh', '-q', '-l', 'fakeuser',
      '-o', 'ControlMaster=auto',
      '-o', 'ControlPersist=yes',
      '-o', 'ControlPath=~/.ssh/ctrl-%C',
      '-o', "ProxyCommand='test'",
      'fakehost', 'true',
    ])

  @mock.patch('subprocess.call')
  def testCleanup(self, mock_call):
    """Tests that the SSH CLI is called with the expected arguments."""
    mock_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    ssh_multi = ssh_multiplexer.SSHMultiplexer(test_state)
    ssh_multi.SetUp('fakehost', 'fakeuser', None, [])
    ssh_multi.CleanUp()

    mock_call.assert_called_with([
      'ssh', '-O', 'exit', '-o', 'ControlPath=~/.ssh/ctrl-%C', 'fakehost'
    ])



if __name__ == '__main__':
  unittest.main()
