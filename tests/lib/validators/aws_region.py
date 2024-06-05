# -*- coding: utf-8 -*-
"""Tests for the AWS region validator."""

import unittest

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import aws_region

class AWSRegionValidatorTest(unittest.TestCase):
  """Tests AWSRegionValidator."""

  def setUp(self):
    """Setup."""
    self.validator = aws_region.AWSRegionValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testawsregion'

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'aws_region')

  def testValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    regions = ['ap-southeast-2', 'us-east-1', 'me-central-1']

    for region in regions:
      val = self.validator.Validate(region, self.recipe_argument)
      self.assertEqual(val, region)

  def testValidateFailure(self):
    """Tests invalid values correctly throw an exception."""
    regions = ['invalid', '123456']

    for r in regions:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          'Invalid AWS Region name'):
        self.validator.Validate(r, self.recipe_argument)


if __name__ == '__main__':
  unittest.main()
