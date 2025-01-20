#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the SCP exporter module."""

import unittest
import mock

from dftimewolf.lib import errors
from dftimewolf.lib.exporters import scp_ex
from tests.lib import modules_test_base


class SCPExporterTest(modules_test_base.ModuleTestBase):
  """Tests for the SCP exporter module."""

  def setUp(self):
    self._InitModule(scp_ex.SCPExporter)
    super().setUp()

  @mock.patch('subprocess.call')
  def testSetup(self, mock_subprocess_call):
    """Tests that the specified directory is used if created."""
    mock_subprocess_call.return_value = 0
    self._module.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'upload', False, True)

    mock_subprocess_call.assert_called_with(
        ['ssh', '-q', '-l', 'fakeuser', 'fakehost', 'true', '-i', 'fakeid'])
    # pylint: disable=protected-access
    self.assertEqual(self._module._destination, '/destination')
    self.assertEqual(self._module._hostname, 'fakehost')
    self.assertEqual(self._module._id_file, 'fakeid')
    self.assertEqual(self._module._paths, ['/path1', '/path2'])
    self.assertEqual(self._module._user, 'fakeuser')

  @mock.patch('subprocess.call')
  def testProcess(self, mock_subprocess_call):
    """Tests that the specified directory is used if created."""
    mock_subprocess_call.return_value = 0
    self._module.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'upload', False, True)
    self._ProcessModule()

    mock_subprocess_call.assert_called_with(
        ['scp', '-i', 'fakeid', '/path1', '/path2',
        'fakeuser@fakehost:/destination'])

  @mock.patch('subprocess.call')
  def testProcessDownload(self, mock_subprocess_call):
    """Tests that the specified directory is used if created."""
    mock_subprocess_call.return_value = 0
    self._module.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'download', False, True)
    self._ProcessModule()

    mock_subprocess_call.assert_called_with(
        ['scp', '-i', 'fakeid',
        'fakeuser@fakehost:/path1', 'fakeuser@fakehost:/path2', '/destination'])

  @mock.patch('subprocess.call')
  def testProcessDownloadExtraSSHOptions(self, mock_subprocess_call):
    """Tests that extra SSH options are taking into account."""
    mock_subprocess_call.return_value = 0
    self._module.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', ['-o', 'foo=bar'],
                       'download', False, True)
    self._ProcessModule()

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
    self._module.SetUp('/path1,/path2', None, 'fakeuser',
                       'fakehost', 'fakeid', ['-o', 'foo=bar'],
                       'download', False, True)
    self._ProcessModule()
    mock_subprocess_call.assert_called_with(
        ['scp', '-o', 'foo=bar', '-i', 'fakeid',
        'fakeuser@fakehost:/path1', 'fakeuser@fakehost:/path2', '/tmp/tmpdir'])

  @mock.patch('subprocess.call')
  def testFailIfUploadWithoutDestination(self, mock_subprocess_call):
    """Tests that the upload module fails if no destination is specified."""
    mock_subprocess_call.return_value = 0
    with self.assertRaises(errors.DFTimewolfError) as error:
      self._module.SetUp('/path1,/path2', None, 'fakeuser',
                         'fakehost', 'fakeid', [], 'upload', False, True)
    self.assertEqual(
      error.exception.message,
      'Destination path must be specified when uploading.')

  @mock.patch('subprocess.call')
  def testProcessDownloadMultiplex(self, mock_subprocess_call):
    """Tests that SSH is called with the correct multiplex parameter."""
    mock_subprocess_call.return_value = 0
    self._module.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'download', True, True)
    self._ProcessModule()

    mock_subprocess_call.assert_called_with(
        ['scp',
         '-o', 'ControlMaster=auto',
         '-o', 'ControlPath=~/.ssh/ctrl-%C',
         '-i', 'fakeid',
        'fakeuser@fakehost:/path1', 'fakeuser@fakehost:/path2', '/destination'])

  @mock.patch('subprocess.call')
  def testProcessDownloadMultiplexCache(self, mock_subprocess_call):
    """Tests that SSH is called with the correct multiplex parameter."""
    mock_subprocess_call.return_value = 0
    self._module.state.AddToCache('ssh_control', 'cached_ssh_control')
    self._module.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'download', True, True)
    self._ProcessModule()

    mock_subprocess_call.assert_called_with(
        ['scp',
         '-o', 'ControlMaster=auto',
         '-o', 'ControlPath=cached_ssh_control',
         '-i', 'fakeid',
        'fakeuser@fakehost:/path1', 'fakeuser@fakehost:/path2', '/destination'])

  @mock.patch('subprocess.call')
  def testSetupError(self, mock_subprocess_call):
    """Tests that recipe errors out if connection check fails."""
    mock_subprocess_call.return_value = -1
    with self.assertRaisesRegex(
        errors.DFTimewolfError, 'Unable to connect to fakehost.') as error:
      self._module.SetUp('/path1,/path2', '/destination', 'fakeuser',
                         'fakehost', 'fakeid', [], 'upload', False, True)
      self.assertTrue(error.exception.critical)

  @mock.patch('subprocess.call')
  def testProcessError(self, mock_subprocess_call):
    """Tests that failures creating directories are properly caught."""
    mock_subprocess_call.return_value = 0
    # pylint: disable=protected-access
    self._module._CreateDestinationDirectory = mock.Mock()
    self._module.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'upload', False, True)

    mock_subprocess_call.return_value = -1
    with self.assertRaisesRegex(
        errors.DFTimewolfError,
        r"Failed copying \['/path1', '/path2'\]") as error:
      self._ProcessModule()
      self.assertTrue(error.exception.critical)

  @mock.patch('subprocess.call')
  def testCreateDestinationDirectory(self, mock_subprocess_call):
    """Tests that the remote directory is created as expected."""
    mock_subprocess_call.return_value = 0
    self._module.SetUp('/path1,/path2', '/destination', 'fakeuser',
                       'fakehost', 'fakeid', [], 'upload', False, False)

    # pylint: disable=protected-access
    self._module._CreateDestinationDirectory(remote=True)
    mock_subprocess_call.assert_called_with(
      ['ssh', 'fakeuser@fakehost', 'mkdir', '-m', 'g+w', '-p', '/destination']
    )
    self._module._CreateDestinationDirectory(remote=False)
    mock_subprocess_call.assert_called_with(
      ['mkdir', '-m', 'g+w', '-p', '/destination']
    )


if __name__ == '__main__':
  unittest.main()
