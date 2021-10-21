#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the VirusTotal (VT) collector."""

import unittest

from dftimewolf.lib import state
from dftimewolf.lib.collectors import virustotal

from dftimewolf import config

FAKE_VT_API_KEY = '123456789'

FAKE_Hashes = 'e2a24ab94f865caeacdf2c3ad015f31f23008ac6db8312c2cbfb32e4a5466ea2'

FAKE_VT_TYPE_EVTX = 'evtx'

FAKE_VT_TYPE_PCAP = 'pcap'

FAKE_DIRECTORY = '/tmp/123'


class VTCollectingTest(unittest.TestCase):
  """Tests for the GCP logging collector."""

  def testInitialization(self):
    """Tests that the collector can be initialized."""
    test_state = state.DFTimewolfState(config.Config)
    vt_collector = virustotal.VTCollector(test_state, name='test')
    self.assertIsNotNone(vt_collector)

  def testSetUp2(self):
    """Tests that VTCollector methods are called with the correct
    args.
    """
    test_state = state.DFTimewolfState(config.Config)

    vt_collector = virustotal.VTCollector(test_state, name='test')

    vt_collector.SetUp(
        hashes=FAKE_Hashes,
        vt_api_key=FAKE_VT_API_KEY,
        vt_type=FAKE_VT_TYPE_PCAP,
        directory=FAKE_DIRECTORY)

    self.assertIsNotNone(vt_collector.hashes_list)

    self.assertIn(
        'e2a24ab94f865caeacdf2c3ad015f31f23008ac6db8312c2cbfb32e4a5466ea2',
        vt_collector.hashes_list)

    self.assertIsNotNone(vt_collector)


if __name__ == '__main__':
  unittest.main()
