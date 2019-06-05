# -*- coding: utf-8 -*-
"""Tests for the Report attribute containers."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import containers

class ReportDataTest(unittest.TestCase):
  """Tests for the Report data attribute container."""

  def test_get_attribute_names(self):
    """Tests the get_attribute_names function."""
    attribute_container = containers.Report(module_name='name', text='text')

    expected_attribute_names = ['attributes', 'module_name', 'text']

    attribute_names = sorted(attribute_container.get_attribute_names())

    self.assertEqual(attribute_names, expected_attribute_names)


if __name__ == '__main__':
  unittest.main()
