# -*- coding: utf-8 -*-
"""Tests for the AWS region validator."""

import unittest

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import gcp_zone


class GCPZoneValidatorTest(unittest.TestCase):
  """Tests GCPZoneValidator."""

  def setUp(self):
    """Setup."""
    self.validator = gcp_zone.GCPZoneValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testgcpzone'

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'gcp_zone')

  def testValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    zones = ['asia-east1-a', 'europe-west2-a', 'us-central1-f']

    for zone in zones:
      val = self.validator.Validate(zone, self.recipe_argument)
      self.assertEqual(val, zone)

  def testValidateFailure(self):
    """Tests invalid values correctly throw an exception."""
    zones = ['nope', '123456']

    for zone in zones:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure, 'Invalid GCP Zone name'):
        self.validator.Validate(zone, self.recipe_argument)


if __name__ == '__main__':
  unittest.main()
