#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the SCP exporter module."""

import unittest
import mock

from dftimewolf.lib import state
from dftimewolf.lib import errors
from dftimewolf.lib.exporters import scp_ex

from dftimewolf import config


class SCPExporterTest(unittest.TestCase):
  """Tests for the SCP exporter module."""

  def testInitialization(self):
    """Tests that the exporter can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    local_scp_exporter = scp_ex.SCPExporter(test_state)
    self.assertIsNotNone(local_scp_exporter)

  @mock.patch('subprocess.call')
  def testSetup(self, mock_subprocess_call):
    """Tests that the specified directory is used if created."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'upload', False, True)

    mock_subprocess_call.assert_called_with(
        ['ssh', '-q', '-l', 'fakeuser', 'fakehost', 'true', '-i', 'fakeid'])
    # pylint: disable=protected-access
    self.assertEqual(scp_exporter._destination, '/destination')
    self.assertEqual(scp_exporter._hostname, 'fakehost')
    self.assertEqual(scp_exporter._id_file, 'fakeid')
    self.assertEqual(scp_exporter._paths, ['/path1', '/path2'])
    self.assertEqual(scp_exporter._user, 'fakeuser')

  @mock.patch('subprocess.call')
  def testProcess(self, mock_subprocess_call):
    """Tests that the specified directory is used if created."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'upload', False, True)
    scp_exporter.Process()

    mock_subprocess_call.assert_called_with(
        ['scp', '-i', 'fakeid', '/path1', '/path2',
        'fakeuser@fakehost:/destination'])

  @mock.patch('subprocess.call')
  def testProcessDownload(self, mock_subprocess_call):
    """Tests that the specified directory is used if created."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'download', False, True)
    scp_exporter.Process()

    mock_subprocess_call.assert_called_with(
        ['scp', '-i', 'fakeid',
        'fakeuser@fakehost:/path1', 'fakeuser@fakehost:/path2', '/destination'])

  @mock.patch('subprocess.call')
  def testProcessDownloadExtraSSHOptions(self, mock_subprocess_call):
    """Tests that extra SSH options are taking into account."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', ['-o', 'foo=bar'],
                       'download', False, True)
    scp_exporter.Process()

    mock_subprocess_call.assert_called_with(
        ['scp', '-o', 'foo=bar', '-i', 'fakeid',
        'fakeuser@fakehost:/path1', 'fakeuser@fakehost:/path2', '/destination'])

  @mock.patch('tempfile.mkdtemp')
  @mock.patch('subprocess.call')
  def testProcessDownloadNoDestination(
    self, mock_subprocess_call, mock_mkdtemp):
    """Tests that not specifying the destination will call mkdtemp."""
    mock_subprocess_call.return_value = 0
    mock_mkdtemp.return_value = '/tmp/tmpdir'
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', None, 'fakeuser',
                       'fakehost', 'fakeid', ['-o', 'foo=bar'],
                       'download', False, True)
    scp_exporter.Process()
    mock_subprocess_call.assert_called_with(
        ['scp', '-o', 'foo=bar', '-i', 'fakeid',
        'fakeuser@fakehost:/path1', 'fakeuser@fakehost:/path2', '/tmp/tmpdir'])

  @mock.patch('subprocess.call')
  def testFailIfUploadWithoutDestination(self, mock_subprocess_call):
    """Tests that the upload module fails if no destination is specified."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    with self.assertRaises(errors.DFTimewolfError) as error:
      scp_exporter.SetUp('/path1,/path2', None, 'fakeuser',
                         'fakehost', 'fakeid', [], 'upload', False, True)
    self.assertEqual(
      error.exception.message,
      'Destination path must be specified when uploading.')

  @mock.patch('subprocess.call')
  def testProcessDownloadMultiplex(self, mock_subprocess_call):
    """Tests that SSH is called with the correct multiplex parameter."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'download', True, True)
    scp_exporter.Process()

    mock_subprocess_call.assert_called_with(
        ['scp',
         '-o', 'ControlMaster=auto',
         '-o', 'ControlPath=~/.ssh/ctrl-%C',
         '-i', 'fakeid',
        'fakeuser@fakehost:/path1', 'fakeuser@fakehost:/path2', '/destination'])

  @mock.patch('subprocess.call')
  def testSetupError(self, mock_subprocess_call):
    """Tests that recipe errors out if connection check fails."""
    mock_subprocess_call.return_value = -1
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    with self.assertRaises(errors.DFTimewolfError) as error:
      scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                         'fakehost', 'fakeid', [], 'upload', False, True)

    self.assertEqual(test_state.errors[0], error.exception)
    self.assertEqual(error.exception.message, 'Unable to connect to fakehost.')
    self.assertTrue(error.exception.critical)

  @mock.patch('subprocess.call')
  def testProcessError(self, mock_subprocess_call):
    """Tests that failures creating directories are properly caught."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    # pylint: disable=protected-access
    scp_exporter._CreateDestinationDirectory = mock.Mock()
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'upload', False, True)

    mock_subprocess_call.return_value = -1
    with self.assertRaises(errors.DFTimewolfError) as error:
      scp_exporter.Process()

    self.assertEqual(test_state.errors[0], error.exception)
    self.assertEqual(error.exception.message,
                     "Failed copying ['/path1', '/path2']")
    self.assertTrue(error.exception.critical)

  @mock.patch('subprocess.call')
  def testCreateDestinationDirectory(self, mock_subprocess_call):
    """Tests that the remote directory is created as expected."""
    mock_subprocess_call.return_value = 0
    test_state = state.DFTimewolfState(config.Config)
    scp_exporter = scp_ex.SCPExporter(test_state)
    scp_exporter.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'upload', False, False)

    # pylint: disable=protected-access
    scp_exporter._CreateDestinationDirectory(remote=True)
    mock_subprocess_call.assert_called_with(
      ['ssh', 'fakeuser@fakehost', 'mkdir', '-m', 'g+w', '-p', '/destination']
    )
    scp_exporter._CreateDestinationDirectory(remote=False)
    mock_subprocess_call.assert_called_with(
      ['mkdir', '-m', 'g+w', '-p', '/destination']
    )


if __name__ == '__main__':
  unittest.main()
