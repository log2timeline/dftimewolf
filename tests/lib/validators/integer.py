# -*- coding: utf-8 -*-
"""Tests for the subnet validator."""

from absl.testing import absltest
from absl.testing import parameterized

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import integer


class IntegerValidatorTest(parameterized.TestCase):
  """Tests IntegerValidator."""

  def setUp(self):
    """Setup."""
    self.validator = integer.IntegerValidator()
    self.recipe_argument = resources.RecipeArgument()
    self.recipe_argument.switch = 'testinteger'


  def testInit(self):
    """Tests initialisation."""
    self.assertEqual(self.validator.NAME, 'integer')

  @parameterized.named_parameters(
    ('zero', '0', 0),
    ('five', '5', 5),
    ('fivemill', '5000000', 5000000),
    ('minusfive', '-5', -5),
  )
  def testValidateSuccess(self, in_param, expected):
    """Test that correct values do not throw an exception."""
    result = self.validator.Validate(in_param, self.recipe_argument)
    self.assertEqual(result, expected)

  @parameterized.named_parameters(
      ('str', 'foo'),
      ('float', '5.5')
  )
  def testValidateFailure(self, in_param):
    """Test integer test failure."""
    with self.assertRaisesRegex(
        errors.RecipeArgsValidationFailure,
        'Not a valid integer'):
      self.validator.Validate(in_param, self.recipe_argument)


if __name__ == '__main__':
  absltest.main()
