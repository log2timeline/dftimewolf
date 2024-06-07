# -*- coding: utf-8 -*-
"""Tests for the hostname validator."""

import unittest

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import hostname


class HostnameValidatorTest(unittest.TestCase):
  """Tests the HostnameValidator class."""

  def setUp(self):
    """Setup."""
    self.validator = hostname.HostnameValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testhostname'

  def testInit(self):
    """Tests initialization."""
    self.assertEqual(self.validator.NAME, 'hostname')

  def testValidateSuccess(self):
    """Test successful validation."""
    fqdns = [
      'github.com',
      'grr-client-ubuntu.c.ramoj-playground.internal',
      'www.google.com.au',
      'www.google.co.uk',
      'localhost',
      'grr-server'
    ]
    for fqdn in fqdns:
      val = self.validator.Validate(fqdn, self.recipe_argument)
      self.assertTrue(val)

    self.recipe_argument.validation_params['comma_separated'] = True
    val = self.validator.Validate(','.join(fqdns), self.recipe_argument)
    self.assertTrue(val)

  def testValidationFailure(self):
    """Tests validation failures."""
    fqdns = ['a-.com', '-a.com']
    for fqdn in fqdns:
      with self.assertRaisesRegex(errors.RecipeArgsValidationFailure,
                                  'Not a valid hostname'):
        self.validator.Validate(fqdn, self.recipe_argument)

    self.recipe_argument.validation_params['comma_separated'] = True
    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        'Not a valid hostname'):
      self.validator.Validate(','.join(fqdns), self.recipe_argument)


  def testValidationFailureWithFQDNOnly(self):
    """tests validation fails for flat names when FQDN_ONLY is set."""
    fqdns = ['localhost', 'grr-server']
    self.recipe_argument.validation_params['comma_separated'] = False
    self.recipe_argument.validation_params['fqdn_only'] = True
    for fqdn in fqdns:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          'Not a valid hostname'):
        self.validator.Validate(fqdn, self.recipe_argument)

    self.recipe_argument.validation_params['comma_separated'] = True
    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        'Not a valid hostname'):
      self.validator.Validate(','.join(fqdns), self.recipe_argument)


if __name__ == '__main__':
  unittest.main()
