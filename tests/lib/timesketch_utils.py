#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests timesketch utilities."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import timesketch_utils


class TimesketchAPIClient(unittest.TestCase):
  """Tests for the Timesketch API client."""

  def testInitialization(self):
    """Tests that the processor can be initialized."""
    timesketch_url = 'http://localhost'
    username = 'test'
    password = 'test'
    timesketch_client = timesketch_utils.TimesketchApiClient(
        host_url=timesketch_url, username=username, password=password)
    self.assertIsNotNone(timesketch_client)


if __name__ == '__main__':
  unittest.main()
