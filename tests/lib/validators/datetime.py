# -*- coding: utf-8 -*-
"""Tests for the datetime validator."""

import unittest

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import datetime


class DatetimeValidatorTest(unittest.TestCase):
  """Tests the DatetimeValidator class."""

  FORMAT_STRING = '%Y-%m-%d %H:%M:%S'

  def setUp(self):
    """Setup."""
    self.validator = datetime.DatetimeValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testdatetime'

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'datetime')

  def testRequiredParam(self):
    """Tests an error is thrown if format_string is missing."""
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError,
        'Missing validator parameter: format_string'):
      self.validator.Validate('value', self.recipe_argument)

  def testValidateSuccess(self):
    """Tests a successful validation."""
    self.recipe_argument.validation_params['format_string'] = self.FORMAT_STRING
    date = '2023-12-31 23:29:59'
    val = self.validator.Validate(date, self.recipe_argument)
    self.assertEqual(val, date)

  def testValidateSuccessWithOrder(self):
    """Tests validation success with order parameters."""
    first = '2023-01-01 00:00:00'
    second = '2023-01-02 00:00:00'
    third = '2023-01-03 00:00:00'
    fourth = '2023-01-04 00:00:00'
    fifth = '2023-01-05 00:00:00'

    self.recipe_argument.validation_params['format_string'] = self.FORMAT_STRING
    self.recipe_argument.validation_params['before'] = fourth
    self.recipe_argument.validation_params['after'] = second

    val = self.validator.Validate(third, self.recipe_argument)
    self.assertEqual(val, third)

    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        f'{first} is before {second} but it should be the other way around'):
      self.validator.Validate(first, self.recipe_argument)

    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        f'{fourth} is before {fifth} but it should be the other way around'):
      self.validator.Validate(fifth, self.recipe_argument)

  def testValidateFailureInvalidFormat(self):
    """Tests invalid date formats correctly fail."""
    values = ['value', '2023-12-31', '2023-31-12 23:29:59']
    self.recipe_argument.validation_params['format_string'] = self.FORMAT_STRING
    for value in values:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          f'does not match format {self.FORMAT_STRING}'):
        self.validator.Validate(value, self.recipe_argument)

  # pylint: disable=protected-access
  def testValidateOrder(self):
    """Tests the _ValidateOrder method."""
    first = '2023-01-01 00:00:00'
    second = '2023-01-02 00:00:00'

    # Correct order passes
    val = self.validator._ValidateOrder(first, second, self.FORMAT_STRING)
    self.assertTrue(val)

    # Reverse order fails
    val = self.validator._ValidateOrder(second, first, self.FORMAT_STRING)
    self.assertFalse(val)

if __name__ == '__main__':
  unittest.main()
