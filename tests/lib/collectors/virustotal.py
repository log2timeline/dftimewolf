#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the VirusTotal (VT) collector."""

import unittest
from unittest import mock

from dftimewolf.lib.collectors import virustotal


FAKE_VT_API_KEY = '123456789'

FAKE_Hashes = 'e2a24ab94f865caeacdf2c3ad015f31f23008ac6db8312c2cbfb32e4a5466ea2'

FAKE_VT_TYPE_EVTX = 'evtx'

FAKE_VT_TYPE_PCAP = 'pcap'

FAKE_DIRECTORY = '/tmp/123'


class VTCollectingTest(unittest.TestCase):
  """Tests for the GCP logging collector."""

  def setUp(self):
    super().setUp()

    self._vt_collector = virustotal.VTCollector(
        name='',
        cache_=mock.MagicMock(),
        container_manager_=mock.MagicMock(),
        telemetry_=mock.MagicMock(),
        publish_message_callback=mock.MagicMock())

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    self.assertIsNotNone(self._vt_collector)

  def testSetUp2(self):
    """Tests that VTCollector methods are called with the correct
    args.
    """
    self._vt_collector.SetUp(
        hashes=FAKE_Hashes,
        vt_api_key=FAKE_VT_API_KEY,
        vt_type=FAKE_VT_TYPE_PCAP,
        directory=FAKE_DIRECTORY)

    self.assertIsNotNone(self._vt_collector.hashes_list)

    self.assertIn(
        'e2a24ab94f865caeacdf2c3ad015f31f23008ac6db8312c2cbfb32e4a5466ea2',
        self._vt_collector.hashes_list)


if __name__ == '__main__':
  unittest.main()
