#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the utils module."""

from __future__ import unicode_literals

import os
import shutil
import tarfile
import tempfile
import unittest

import mock

from dftimewolf.lib import utils

import pandas as pd


class UtilsTest(unittest.TestCase):
  """Tests for the utils module."""

  def setUp(self):
    """Test setup."""
    self.tmp_input_dir = tempfile.mkdtemp(prefix='dftimewolf-input')
    self.tmp_output_dir = tempfile.mkdtemp(prefix='dftimewolf-output')

  def tearDown(self):
    """Tears Down class."""
    if 'dftimewolf-input' in self.tmp_input_dir:
      shutil.rmtree(self.tmp_input_dir)
    if 'dftimewolf-output' in self.tmp_output_dir:
      shutil.rmtree(self.tmp_output_dir)

  @mock.patch('tempfile.mkdtemp')
  def testCompress(self, mock_mkdtemp):
    """Tests the utils.Compress() method."""
    test_data = 'SampleInput'
    test_name = 'test_file.txt'
    mock_mkdtemp.return_value = self.tmp_output_dir
    test_file = os.path.join(self.tmp_input_dir, test_name)
    with open(test_file, 'w') as test_file_fh:
      test_file_fh.write(test_data)

    output_file = utils.Compress(self.tmp_input_dir)
    self.assertTrue(os.path.exists(output_file))
    self.assertTrue(tarfile.is_tarfile(output_file))

    tar = tarfile.TarFile.open(output_file)
    member_name = tar.getmembers()[1].name
    self.assertIn(test_name, member_name)
    member_data = (
        tar.extractfile(member_name).read())  # pytype: disable=attribute-error
    self.assertEqual(member_data, test_data.encode('utf-8'))

  def testWriteDataFrameToJsonl(self):
    """Tests the utils.WriteDataFrameToJsonl() method."""
    sample_df = pd.DataFrame([1], [0], ['foo'])
    expected_jsonl = '{"foo":1}\n'

    filename = utils.WriteDataFrameToJsonl(sample_df)

    with open(filename) as f:
      contents = ''.join(f.readlines())

    self.assertEqual(contents, expected_jsonl)
