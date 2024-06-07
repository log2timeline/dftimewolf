# -*- coding: utf-8 -*-
"""Tests for the regex validator."""

import unittest

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import regex


class RegexValidatorTest(unittest.TestCase):
  """Tests RegexValidator."""

  def setUp(self):
    """Setup."""
    self.validator = regex.RegexValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testregex'
    self.recipe_argument.validation_params = {'comma_separated': True}

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'regex')

  def testValidateSuccess(self):
    """Test that correct values do not throw an exception."""
    values = ['abcdef', 'bcdefg', 'abcdef,bcdefg']
    self.recipe_argument.validation_params['regex'] = '.?bcdef.?'
    for value in values:
      valid_value = self.validator.Validate(value, self.recipe_argument)
      self.assertEqual(valid_value, value)

  def testValidateFailure(self):
    """Test Regex test failure."""
    self.recipe_argument.validation_params['regex'] = '.?bcdef.?'

    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        "does not match regex /.\?bcdef.\?"): # pylint: disable=anomalous-backslash-in-string
      self.validator.Validate('tuvwxy', self.recipe_argument)

  def testRequiredParam(self):
    """Tests an error is thrown is the regex param is missing."""
    self.recipe_argument.validation_params['regex'] = None
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        'Missing validator parameter: regex'):
      self.validator.Validate('tuvwxy', self.recipe_argument)


if __name__ == '__main__':
  unittest.main()
