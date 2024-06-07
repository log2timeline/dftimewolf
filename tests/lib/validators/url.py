# -*- coding: utf-8 -*-
"""Tests for the URL validator."""

import unittest

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import url


class URLValidatorTest(unittest.TestCase):
  """Tests the URLValidator class."""

  def setUp(self):
    """Setup."""
    self.validator = url.URLValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testurl'

  def testInit(self):
    """Tests initialization."""
    self.assertEqual(self.validator.NAME, 'url')

  def testValidateSuccess(self):
    """Test successful validation."""
    fqdns = [
        'http://10.100.0.100:8080',
        'http://10.100.0.100',
        'https://10.100.0.100',
        'http://localhost:8080',
        'http://grr-server:8080',
        'http://grr.ramoj-playground.internal:8080',
        'http://grr.ramoj-playground.internal',
        'https://grr.ramoj-playground.internal',
    ]
    for fqdn in fqdns:
      val = self.validator.Validate(fqdn, self.recipe_argument)
      self.assertTrue(val, f'{fqdn} failed validation')

    self.recipe_argument.validation_params['comma_separated'] = True
    val = self.validator.Validate(','.join(fqdns), self.recipe_argument)
    self.assertTrue(val)

  def testValidationFailure(self):
    """Tests validation failures."""
    fqdns = [
        'value',
        '10.100.0.100',  # Needs scheme
    ]
    for fqdn in fqdns:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          "Not a valid URL"):
        self.validator.Validate(fqdn, self.recipe_argument)

    self.recipe_argument.validation_params['comma_separated'] = True
    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure, "Error: Not a valid URL"):
      self.validator.Validate(','.join(fqdns), self.recipe_argument)

if __name__ == '__main__':
  unittest.main()
