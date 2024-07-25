# -*- coding: utf-8 -*-
"""Validator for integers."""

from dftimewolf.lib import errors, resources, args_validator
from dftimewolf.lib.validators import manager as validators_manager


class IntegerValidator(args_validator.AbstractValidator):
  """Validates an integer."""

  NAME = 'integer'

  def Validate(self,
              argument_value: str,
              recipe_argument: resources.RecipeArgument) -> int:
    """Validate that the argument_value is a valid integer.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      A parsed integer.

    Raises:
      errors.RecipeArgsValidationFailure: If the argument is not an integer.
    """
    try:
      return int(argument_value)
    except ValueError:
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Not a valid integer')


validators_manager.ValidatorsManager.RegisterValidator(IntegerValidator)
