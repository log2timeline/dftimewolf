#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the GRR hunt collectors."""

from __future__ import unicode_literals

import unittest

import mock

from dftimewolf.lib import state
from dftimewolf.lib.collectors import grr_hunt


class GRRArtifactCollectorTest(unittest.TestCase):
  """Tests for the GRR artifact collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_hunt_artifact_collector = grr_hunt.GRRHuntArtifactCollector(test_state)
    self.assertIsNotNone(grr_hunt_artifact_collector)


class GRRFileCollectorTest(unittest.TestCase):
  """Tests for the GRR file collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_hunt_file_collector = grr_hunt.GRRHuntFileCollector(test_state)
    self.assertIsNotNone(grr_hunt_file_collector)


class GRRFHuntDownloader(unittest.TestCase):
  """Tests for the GRR hunt downloader."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState()
    grr_hunt_downloader = grr_hunt.GRRHuntDownloader(test_state)
    self.assertIsNotNone(grr_hunt_downloader)

  @mock.patch('os.remove')
  @mock.patch('zipfile.ZipFile.extract')
  def testExtractHuntResults(self, unused_mock_extract, mock_remove):
    """Tests that hunt results are correctly extracted."""
    test_state = state.DFTimewolfState()
    grr_hunt_downloader = grr_hunt.GRRHuntDownloader(test_state)
    grr_hunt_downloader.output_path = '/directory'
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
    result = sorted(grr_hunt_downloader._extract_hunt_results(test_zip))
    self.assertEqual(result, expected)
    mock_remove.assert_called_with('tests/lib/collectors/test_data/hunt.zip')


if __name__ == '__main__':
  unittest.main()
