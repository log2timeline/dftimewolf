# -*- coding: utf-8 -*-
"""Validator for regular expression matches."""
from typing import Any

import re

from dftimewolf.lib import errors, resources, args_validator
from dftimewolf.lib.validators import manager as validators_manager


class RegexValidator(args_validator.CommaSeparatedValidator):
  """Validates a string according to a regular expression."""

  NAME = 'regex'

  def ValidateSingle(self,
                     argument_value: Any,
                     recipe_argument: resources.RecipeArgument) -> str:
    """Validate a string according to a regular expression.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      str: a valid string.

    Raises:
      errors.RecipeArgsValidatorError: If no regex is found to use.
      errors.RecipeArgsValidationFailure: If the argument value does not match
        the regex.
    """
    if not isinstance(argument_value, str):
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Argument value must be a string.')
    expression = recipe_argument.validation_params.get('regex')
    if expression is None:
      raise errors.RecipeArgsValidatorError(
          'Missing validator parameter: regex')

    regex = re.compile(expression)

    if not regex.match(argument_value):
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          f'does not match regex /{expression}/')

    return argument_value

validators_manager.ValidatorsManager.RegisterValidator(RegexValidator)
