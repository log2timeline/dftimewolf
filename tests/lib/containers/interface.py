#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the attribute container interface."""

import unittest

from dftimewolf.lib.containers import interface


class AttributeContainerTest(unittest.TestCase):
  """Tests for the attribute container interface."""

  def testGetAttributeNames(self):
    """Tests the GetAttributeNames function."""
    attribute_container = interface.AttributeContainer()
    attribute_container.attribute_name = 'attribute_name'
    attribute_container.attribute_value = 'attribute_value'

    expected_attribute_names = ['attribute_name', 'attribute_value']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)


if __name__ == '__main__':
  unittest.main()
