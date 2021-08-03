#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Metawolf."""

import os
import unittest
import typing
from dftimewolf.metawolf import metawolf


class MetawolfTest(unittest.TestCase):
  """Integration tests for Metawolf."""

  @classmethod
  @typing.no_type_check
  def setUpClass(cls) -> None:
    # Always load the same default session
    cls.session_file = './metawolf-test-session.json'
    # After that the default session is loaded, use a tmp file for outputs
    cls.tmp_file = '/tmp/metawolf-test'

  @typing.no_type_check
  def testSet(self) -> None:
    """Test the `set` command."""
    m = metawolf.Metawolf(
        session_path=self.session_file,
        transcript_files=['./transcripts/set.txt'])
    m.metawolf_utils.session_path = self.tmp_file
    # Exit code should be 0 if the test succeeded
    self.assertEqual(0, m.cmdloop())

  @classmethod
  @typing.no_type_check
  def tearDownClass(cls) -> None:
    try:
      os.remove(cls.tmp_file)
    except IOError:
      pass
