#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR hunt collectors."""

import unittest
import zipfile
import mock

from grr_response_proto import flows_pb2

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib.collectors import grr_hunt
from tests.lib.collectors.test_data import mock_grr_hosts


# Mocking of classes.
# pylint: disable=invalid-name
class GRRHuntArtifactCollectorTest(unittest.TestCase):
  """Tests for the GRR artifact collector."""

  def setUp(self):
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_hunt_artifact_collector = grr_hunt.GRRHuntArtifactCollector(
        self.test_state)
    self.grr_hunt_artifact_collector.SetUp(
        artifacts='RandomArtifact',
        use_tsk=True,
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2'
    )

  @mock.patch('grr_api_client.hunt.CreateHunt')
  def testProcess(self, mock_CreateHunt):
    """Tests that the process function issues correct GRR API calls."""
    self.grr_hunt_artifact_collector.Process()
    call_kwargs = mock_CreateHunt.call_args[1]  # extract call kwargs
    self.assertEqual(call_kwargs['flow_args'].artifact_list,
                     ['RandomArtifact'])
    self.assertEqual(call_kwargs['flow_args'].use_tsk, True)
    self.assertEqual(call_kwargs['flow_name'], 'ArtifactCollectorFlow')
    self.assertEqual(call_kwargs['hunt_runner_args'].description,
                     'random reason')


class GRRHuntFileCollectorTest(unittest.TestCase):
  """Tests for the GRR file collector."""

  def setUp(self):
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_hunt_file_collector = grr_hunt.GRRHuntFileCollector(
        self.test_state)
    self.grr_hunt_file_collector.SetUp(
        file_path_list='/etc/passwd,/etc/shadow',
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2'
    )

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertEqual(
        self.grr_hunt_file_collector.file_path_list,
        ['/etc/passwd', '/etc/shadow']
    )

  @mock.patch('grr_api_client.hunt.CreateHunt')
  def testProcess(self, mock_CreateHunt):
    """Tests that the process method invokes the correct GRR API calls."""
    self.grr_hunt_file_collector.Process()
    call_kwargs = mock_CreateHunt.call_args[1]  # extract call kwargs
    self.assertEqual(call_kwargs['flow_args'].paths,
                     ['/etc/passwd', '/etc/shadow'])
    self.assertEqual(call_kwargs['flow_args'].action.action_type,
                     flows_pb2.FileFinderAction.DOWNLOAD)
    self.assertEqual(call_kwargs['flow_name'], 'FileFinder')
    self.assertEqual(call_kwargs['hunt_runner_args'].description,
                     'random reason')



class GRRFHuntDownloader(unittest.TestCase):
  """Tests for the GRR hunt downloader."""

  def setUp(self):
    self.test_state = state.DFTimewolfState(config.Config)
    self.grr_hunt_downloader = grr_hunt.GRRHuntDownloader(self.test_state)
    self.grr_hunt_downloader.SetUp(
        hunt_id='H:12345',
        reason='random reason',
        grr_server_url='http://fake/endpoint',
        grr_username='admin',
        grr_password='admin',
        approvers='approver1,approver2'
    )
    self.grr_hunt_downloader.output_path = '/tmp/test'

  def testInitialization(self):
    """Tests that the collector is correctly initialized."""
    self.assertEqual(self.grr_hunt_downloader.hunt_id, 'H:12345')

  @mock.patch('dftimewolf.lib.collectors.grr_hunt.GRRHuntDownloader._ExtractHuntResults')  # pylint: disable=line-too-long
  @mock.patch('dftimewolf.lib.collectors.grr_hunt.GRRHuntDownloader._GetAndWriteArchive')  # pylint: disable=line-too-long
  @mock.patch('grr_api_client.hunt.HuntRef.Get')
  def testCollectHuntResults(self,
                             mock_Get,
                             mock_get_write_archive,
                             mock_ExtractHuntResults):
    """Tests that hunt results are downloaded to the correct file."""
    mock_Get.return_value = mock_grr_hosts.MOCK_HUNT
    self.grr_hunt_downloader.Process()
    mock_get_write_archive.assert_called_with(mock_grr_hosts.MOCK_HUNT,
                                              '/tmp/test/H:12345.zip')
    mock_ExtractHuntResults.assert_called_with('/tmp/test/H:12345.zip')

  @mock.patch('os.remove')
  @mock.patch('zipfile.ZipFile.extract')
  def testExtractHuntResults(self, _, mock_remove):
    """Tests that hunt results are correctly extracted."""
    self.grr_hunt_downloader.output_path = '/directory'
    expected = sorted([
        ('greendale-student04.c.greendale.internal',
         '/directory/hunt_H_A43ABF9D/C.4c4223a2ea9cf6f1'),
        ('greendale-admin.c.greendale.internal',
         '/directory/hunt_H_A43ABF9D/C.ba6b63df5d330589'),
        ('greendale-student05.c.greendale.internal',
         '/directory/hunt_H_A43ABF9D/C.fc693a148af801d5')
    ])
    test_zip = 'tests/lib/collectors/test_data/hunt.zip'
    # pylint: disable=protected-access
    result = sorted(self.grr_hunt_downloader._ExtractHuntResults(test_zip))
    self.assertEqual(result, expected)
    mock_remove.assert_called_with('tests/lib/collectors/test_data/hunt.zip')

  @mock.patch('os.remove')
  @mock.patch('zipfile.ZipFile.extract')
  def testOSErrorExtractHuntResults(self, mock_extract, mock_remove):
    """Tests that an OSError when reading files generate errors."""
    self.grr_hunt_downloader.output_path = '/directory'
    test_zip = 'tests/lib/collectors/test_data/hunt.zip'
    mock_extract.side_effect = OSError
    # pylint: disable=protected-access
    result = self.grr_hunt_downloader._ExtractHuntResults(test_zip)
    self.assertEqual(result, [])
    self.assertEqual(
        self.test_state.errors[0],
        ('Error manipulating file tests/lib/collectors/test_data/hunt.zip: ',
         True)
    )
    mock_remove.assert_not_called()

  @mock.patch('os.remove')
  @mock.patch('zipfile.ZipFile.extract')
  def testBadZipFileExtractHuntResults(self, mock_extract, mock_remove):
    """Tests that a BadZipFile error when reading files generate errors."""
    self.grr_hunt_downloader.output_path = '/directory'
    test_zip = 'tests/lib/collectors/test_data/hunt.zip'

    mock_extract.side_effect = zipfile.BadZipfile
    # pylint: disable=protected-access
    result = self.grr_hunt_downloader._ExtractHuntResults(test_zip)
    self.assertEqual(result, [])
    self.assertEqual(
        self.test_state.errors[0],
        ('Bad zipfile tests/lib/collectors/test_data/hunt.zip: ', True)
    )
    mock_remove.assert_not_called()


if __name__ == '__main__':
  unittest.main()
