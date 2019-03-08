#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the attribute container interface."""

from __future__ import unicode_literals

import unittest

from dftimewolf.lib.containers import interface


class AttributeContainerIdentifierTest(unittest.TestCase):
  """Tests for the attribute container identifier."""

  def test_copy_to_string(self):
    """Tests the copy_to_string function."""
    identifier = interface.AttributeContainerIdentifier()

    expected_identifier_string = '{0:d}'.format(id(identifier))
    identifier_string = identifier.copy_to_string()
    self.assertEqual(identifier_string, expected_identifier_string)


class AttributeContainerTest(unittest.TestCase):
  """Tests for the attribute container interface."""

  def test_copy_to_dict(self):
    """Tests the copy_to_dict function."""
    attribute_container = interface.AttributeContainer()
    attribute_container.attribute_name = 'attribute_name'
    attribute_container.attribute_value = 'attribute_value'

    expected_dict = {
        'attribute_name': 'attribute_name',
        'attribute_value': 'attribute_value'}

    test_dict = attribute_container.copy_to_dict()

    self.assertEqual(test_dict, expected_dict)

  def test_get_attribute_names(self):
    """Tests the get_attribute_names function."""
    attribute_container = interface.AttributeContainer()
    attribute_container.attribute_name = 'attribute_name'
    attribute_container.attribute_value = 'attribute_value'

    expected_attribute_names = ['attribute_name', 'attribute_value']

    attribute_names = sorted(attribute_container.get_attribute_names())

    self.assertEqual(attribute_names, expected_attribute_names)

  def test_get_attributes(self):
    """Tests the get_attributes function."""
    attribute_container = interface.AttributeContainer()
    attribute_container.attribute_name = 'attribute_name'
    attribute_container.attribute_value = 'attribute_value'

    expected_attributes = [
        ('attribute_name', 'attribute_name'),
        ('attribute_value', 'attribute_value')]

    attributes = sorted(attribute_container.get_attributes())

    self.assertEqual(attributes, expected_attributes)

  def test_get_attribute_values_hash(self):
    """Tests the get_attribute_values_hash function."""
    attribute_container = interface.AttributeContainer()
    attribute_container.attribute_name = 'attribute_name'
    attribute_container.attribute_value = 'attribute_value'

    attribute_values_hash1 = attribute_container.get_attribute_values_hash()

    attribute_container.attribute_value = 'changes'

    attribute_values_hash2 = attribute_container.get_attribute_values_hash()

    self.assertNotEqual(attribute_values_hash1, attribute_values_hash2)

  def test_get_attribute_values_string(self):
    """Tests the get_attribute_values_string function."""
    attribute_container = interface.AttributeContainer()
    attribute_container.attribute_name = 'attribute_name'
    attribute_container.attribute_value = 'attribute_value'

    attribute_values_string1 = attribute_container.get_attribute_values_string()

    attribute_container.attribute_value = 'changes'

    attribute_values_string2 = attribute_container.get_attribute_values_string()

    self.assertNotEqual(attribute_values_string1, attribute_values_string2)

  def test_get_identifier(self):
    """Tests the get_identifier function."""
    attribute_container = interface.AttributeContainer()

    identifier = attribute_container.get_identifier()

    self.assertIsNotNone(identifier)

  def test_get_session_identifier(self):
    """Tests the get_session_identifier function."""
    attribute_container = interface.AttributeContainer()

    session_identifier = attribute_container.get_session_identifier()

    self.assertIsNone(session_identifier)

  def test_set_identifier(self):
    """Tests the set_identifier function."""
    attribute_container = interface.AttributeContainer()

    attribute_container.set_identifier(None)

  def test_set_session_identifier(self):
    """Tests the set_session_identifier function."""
    attribute_container = interface.AttributeContainer()

    attribute_container.set_session_identifier(None)


if __name__ == '__main__':
  unittest.main()
