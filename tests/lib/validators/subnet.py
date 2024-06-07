# -*- coding: utf-8 -*-
"""Tests for the subnet validator."""

import unittest

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import subnet


class SubnetValidatorTest(unittest.TestCase):
  """Tests SubnetValidator."""

  def setUp(self):
    """Setup."""
    self.validator = subnet.SubnetValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testsubnet'
    self.recipe_argument.validation_params = {'comma_separated': True}


  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'subnet')

  def testValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    values = ['1.2.3.4/32','192.168.0.0/24','1.2.3.4/32,192.168.0.0/24']
    for value in values:
      valid_value = self.validator.Validate(value, self.recipe_argument)
      self.assertEqual(valid_value, value)

  def testValidateFailure(self):
    """Test Subnet test failure."""
    values = ['1.2.3.4/33', '267.0.0.1/32', 'text']

    for value in values:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          'Not a valid subnet'):
        self.validator.Validate(value, self.recipe_argument)


if __name__ == '__main__':
  unittest.main()
