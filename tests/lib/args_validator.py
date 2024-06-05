"""Tests args_validator classes."""

import unittest
import mock

from dftimewolf.lib import args_validator
from dftimewolf.lib import resources
from dftimewolf.lib import errors


# pylint: disable=abstract-class-instantiated
# pytype: disable=not-instantiable
class CommaSeparatedValidatorTest(unittest.TestCase):
  """Tests CommaSeparatedValidator."""

  def testInit(self):
    """Tests initialization.

    Really, CommaSeparatedValidator is an abstract class so should never be
    instantiated, but we're doing this for unit tests, so we can test the
    non-abstract method."""
    args_validator.CommaSeparatedValidator.__abstractmethods__=set()

    # pylint: disable=unused-variable
    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           '__init__',
                           return_value=None) as mock_init:
      validator = args_validator.CommaSeparatedValidator()
      mock_init.assert_called_once()
    # pylint: enable=unused-variable

  def testValidate(self):
    """Tests validation."""
    args_validator.CommaSeparatedValidator.__abstractmethods__=set()

    recipe_argument = resources.RecipeArgument()
    recipe_argument.switch = 'testcommaseparated'

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           side_effect=lambda x, y: x) as mock_validatesingle:
      validator = args_validator.CommaSeparatedValidator()
      recipe_argument.validation_params = {'comma_separated': True}
      val = validator.Validate('one,two,three', recipe_argument)
      self.assertEqual(mock_validatesingle.call_count, 3)
      self.assertEqual(val,'one,two,three')

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           side_effect=lambda x, y: x) as mock_validatesingle:
      validator = args_validator.CommaSeparatedValidator()
      recipe_argument.validation_params = {'comma_separated': False}
      val = validator.Validate('one,two,three', recipe_argument)
      self.assertEqual(mock_validatesingle.call_count, 1)
      self.assertEqual(val,'one,two,three')

    with mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           side_effect=lambda x, y: x):
      validator = args_validator.CommaSeparatedValidator()
      recipe_argument.validation_params = {}
      val = validator.Validate('one,two,three', recipe_argument)
      self.assertEqual(mock_validatesingle.call_count, 1)
      self.assertEqual(val, 'one,two,three')

  def testValidateFailure(self):
    """Tests validation failure."""
    def FailingValidateSingle(argument_value, _):
      if argument_value == 'three':
        raise errors.RecipeArgsValidationFailure(
            'failingvalidatesingle',
            'three',
            'CommaSeperatedValidator',
            'TestDescription')
      return argument_value

    with (mock.patch.object(args_validator.CommaSeparatedValidator,
                           'ValidateSingle',
                           side_effect=FailingValidateSingle)):
      validator = args_validator.CommaSeparatedValidator()
      argument_definition = resources.RecipeArgument()
      argument_definition.validation_params = {'comma_separated': True}
      with self.assertRaises(errors.RecipeArgsValidationFailure):
        validator.Validate('one,two,three', argument_definition)


if __name__ == '__main__':
  unittest.main()
