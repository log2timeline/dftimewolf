#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Metawolf output utilities."""

import unittest
from unittest import mock

import typing

from dftimewolf.metawolf import output

MOCK_PROCESS_JSON = {
    'session_id': 'session_test',
    'recipe': 'recipe_test',
    'cmd_readable': '-c \'import time; time.sleep(3)\'',
    'output_id': 0,
    'cmd_id': 'id_test',
    'outfile_path': 'path_test',
    'timestamp': 'timestamp_test',
    'interrupted': False
}


class MetawolfOutputTests(unittest.TestCase):
  """Test output.py"""

  def testColor(self) -> None:
    """Test that outputs are color formatted correctly."""
    colored_string = output.MetawolfOutput().Color('test_string', output.GREEN)
    expected_string = '\033[92mtest_string\033[0m'
    self.assertEqual(expected_string, colored_string)


class MetawolfProcessTest(unittest.TestCase):
  """Test output.py"""

  @mock.patch('dftimewolf.metawolf.output.MetawolfProcess.Read')
  @mock.patch('dftimewolf.metawolf.output.MetawolfProcess.Poll')
  @typing.no_type_check
  def testStatus(self, mock_poll, mock_read) -> None:
    """Test that the inferred process status is correct."""
    metawolf_process = output.MetawolfProcess(from_dict=MOCK_PROCESS_JSON)
    # In this test we use "assertIn" since the output contains terminal color
    # codes.

    mock_poll.return_value = None
    self.assertIn('Running', metawolf_process.Status())

    mock_poll.return_value = -1
    self.assertIn('Unknown', metawolf_process.Status())

    mock_poll.return_value = 1
    mock_read.return_value = output.CRITICAL_ERROR
    self.assertIn('Failed', metawolf_process.Status())

    mock_poll.return_value = 0
    mock_read.return_value = ''
    self.assertIn('Completed', metawolf_process.Status())

  @typing.no_type_check
  def testMarshal(self) -> None:
    """Test that a Metawolf process is marshaled to a JSON dict correctly."""
    metawolf_process = output.MetawolfProcess(from_dict=MOCK_PROCESS_JSON)
    self.assertEqual(MOCK_PROCESS_JSON, metawolf_process.Marshal())
