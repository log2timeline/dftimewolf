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

    expected_attribute_names = [
        'attribute_name', 'attribute_value', 'metadata']

    attribute_names = sorted(attribute_container.GetAttributeNames())

    self.assertEqual(attribute_names, expected_attribute_names)

  def testSetMetadata(self):
    """Tests setting and retrieving metadata set on a container."""
    cont = interface.AttributeContainer()
    cont.SetMetadata('source_module', 'example_module_name')

    self.assertEqual(len(cont.metadata.keys()), 1)
    self.assertEqual(cont.metadata['source_module'], 'example_module_name')


if __name__ == '__main__':
  unittest.main()
