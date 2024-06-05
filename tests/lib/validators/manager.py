# -*- coding: utf-8 -*-
"""Tests for the validator manager."""

import unittest

from dftimewolf.lib import args_validator, errors, resources
from dftimewolf.lib.validators import manager


class _TestValidator(args_validator.AbstractValidator):
  """Validator class for unit tests."""
  NAME = 'test'

  def Validate(self, argument_value, recipe_argument):
    return argument_value


class _TestValidator2(args_validator.AbstractValidator):
  """Validator class for unit tests."""
  NAME = 'test2'

  def Validate(self, argument_value, recipe_argument):
    return argument_value


class ValidatorsManagerTest(unittest.TestCase):
  """Tests for the validators manager."""

  # pylint: disable=protected-access
  def testRegistration(self):
    """Tests the RegisterValidator and DeregisterValidator functions."""
    number_of_validator_classes = len(
        manager.ValidatorsManager._validator_classes)

    manager.ValidatorsManager.RegisterValidator(_TestValidator)
    self.assertEqual(
        len(manager.ValidatorsManager._validator_classes),
        number_of_validator_classes + 1)

    manager.ValidatorsManager.DeregisterValidator(_TestValidator)
    self.assertEqual(
        len(manager.ValidatorsManager._validator_classes),
        number_of_validator_classes)

  def testRegisterValidators(self):
    """Tests the RegisterValidators function."""
    number_of_validator_classes = len(
        manager.ValidatorsManager._validator_classes)

    manager.ValidatorsManager.RegisterValidators(
        [_TestValidator, _TestValidator2])
    self.assertEqual(
        len(manager.ValidatorsManager._validator_classes),
        number_of_validator_classes + 2)

    manager.ValidatorsManager.DeregisterValidator(_TestValidator)
    manager.ValidatorsManager.DeregisterValidator(_TestValidator2)

    self.assertEqual(
        number_of_validator_classes,
        len(manager.ValidatorsManager._validator_classes))

  def testValidate(self):
    """Tests the Validate function."""
    recipe_argument = resources.RecipeArgument()
    recipe_argument.validation_params = {'format': 'test'}

    manager.ValidatorsManager.RegisterValidator(_TestValidator)

    validation_result = manager.ValidatorsManager.Validate(
        'test', recipe_argument)
    self.assertEqual(validation_result, 'test')

    recipe_argument.validation_params['format'] = 'does_not_exist'
    with self.assertRaisesRegex(
        errors.RecipeArgsValidatorError, 'not a registered validator'):
      manager.ValidatorsManager.Validate('test', recipe_argument)

  def testListValidators(self):
    """Tests the ListValidators function."""
    registered_validators = manager.ValidatorsManager.ListValidators()
    self.assertNotIn(_TestValidator.NAME, registered_validators)
    manager.ValidatorsManager.RegisterValidator(_TestValidator)

    registered_validators = manager.ValidatorsManager.ListValidators()
    self.assertIn(_TestValidator.NAME, registered_validators)
    manager.ValidatorsManager.DeregisterValidator(_TestValidator)


if __name__ == '__main__':
  unittest.main()
