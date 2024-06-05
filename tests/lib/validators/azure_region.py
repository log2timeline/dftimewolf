# -*- coding: utf-8 -*-
"""Tests for the Azure region validator."""

import unittest

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import azure_region


class AzureRegionValidatorTest(unittest.TestCase):
  """Tests AzureRegionValidator."""

  def setUp(self):
    """Setup."""
    self.validator = azure_region.AzureRegionValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testazureregion'

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'azure_region')

  def testValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    regions = ['eastasia', 'norwaywest', 'westindia']

    for region in regions:
      val  = self.validator.Validate(region, self.recipe_argument)
      self.assertEqual(val, region)

  def testValidateFailure(self):
    """Tests invalid values correctly throw an exception."""
    regions = ['invalid', '123456']

    for region in regions:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          'Invalid Azure Region name'):
        self.validator.Validate(region, self.recipe_argument)


if __name__ == '__main__':
  unittest.main()
