# -*- coding: utf-8 -*-
"""Tests for the Report attribute containers."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib import datatypes

class ReportDataTest(unittest.TestCase):
  """Tests for the Report data attribute container."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = datatypes.Report(module_name='name', text='text')

    expected_attribute_names = ['module_name', 'text']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


if __name__ == '__main__':
  unittest.main()
