# -*- coding: utf-8 -*-
"""Tests for the datetime validator."""

import datetime
import unittest

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import datetime_validator


class DatetimeValidatorTest(unittest.TestCase):
  """Tests the DatetimeValidator class."""

  FORMAT_STRING = '%Y-%m-%d %H:%M:%S'

  def setUp(self):
    """Setup."""
    self.validator = datetime_validator.DatetimeValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testdatetime'

  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'datetime')

  def testValidateSuccess(self):
    """Tests a successful validation."""
    date_value = datetime.datetime(
        2023, 12, 31, 23, 29, 59, tzinfo=datetime.timezone.utc)
    date_string = '2023-12-31 23:29:59'
    val = self.validator.Validate(date_string, self.recipe_argument)
    self.assertEqual(val, date_value)

  def testValidateSuccessWithOrder(self):
    """Tests validation success with order parameters."""
    first_string = '2023-01-01 00:00:00'
    second_string = '2023-01-02 00:00:00'
    third_string = '2023-01-03 00:00:00'
    third_datetime = datetime.datetime(
        2023, 1, 3, 0, 0, 0, tzinfo=datetime.timezone.utc)
    fourth_string = '2023-01-04 00:00:00'
    fifth_string = '2023-01-05 00:00:00'

    self.recipe_argument.validation_params['before'] = fourth_string
    self.recipe_argument.validation_params['after'] = second_string

    val = self.validator.Validate(third_string, self.recipe_argument)
    self.assertEqual(val, third_datetime)

    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        'but it should be the other way around'):
      self.validator.Validate(first_string, self.recipe_argument)

    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        'but it should be the other way around'):
      self.validator.Validate(fifth_string, self.recipe_argument)

  def testValidateFailureInvalidFormat(self):
    """Tests invalid date formats correctly fail."""
    # There is no February 31st
    values = ['value', '2023-02-31', '2023-31-12 23:29:59']
    for value in values:
      with self.assertRaisesRegex(
          errors.RecipeArgsValidationFailure,
          'is not a valid datetime'):
        self.validator.Validate(value, self.recipe_argument)

  # pylint: disable=protected-access
  def testValidateOrder(self):
    """Tests the _ValidateOrder method."""
    first = '2023-01-01 00:00:00'
    second = '2023-01-02 00:00:00'

    # Correct order passes
    val = self.validator._ValidateOrder(first, second)
    self.assertTrue(val)

    # Reverse order fails
    val = self.validator._ValidateOrder(second, first) #pylint: disable=arguments-out-of-order
    self.assertFalse(val)

class EndTimeValidatorTest(unittest.TestCase):
  """Tests the EndTimeValidator class."""

  def setUp(self):
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'end_time'
    self.validator = datetime_validator.EndTimeValidator()

  def testValidate(self):
    """Tests the validate method."""
    timeless_string = '20240101'
    val = self.validator.Validate(timeless_string, self.recipe_argument)
    self.assertEqual(val, datetime.datetime(
        2024, 1, 1, 23, 59, 59, tzinfo=datetime.timezone.utc))

    string_with_time = '2024-01-01 09:13:00'
    val = self.validator.Validate(string_with_time, self.recipe_argument)
    self.assertEqual(val, datetime.datetime(
        2024, 1, 1, 9, 13, 0, tzinfo=datetime.timezone.utc))

if __name__ == '__main__':
  unittest.main()
