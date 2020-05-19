#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests timesketch utilities."""

import unittest

from dftimewolf import config
from dftimewolf.lib import state
from dftimewolf.lib import timesketch_utils

class FakeTimesketchApiClient(object):
  """Fake API Client Class."""
  TYPE = 'client'


class TimesketchUtilsTest(unittest.TestCase):
  """Tests for the Timesketch utils."""

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    wolf_config = config.Config()
    wolf_state = state.DFTimewolfState(wolf_config)
    wolf_state.AddToCache('timesketch_client', FakeTimesketchApiClient())

    timesketch_client = timesketch_utils.GetApiClient(wolf_state)
    self.assertIsNotNone(timesketch_client)


if __name__ == '__main__':
  unittest.main()
