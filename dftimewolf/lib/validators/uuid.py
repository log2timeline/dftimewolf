# -*- coding: utf-8 -*-
"""Validator for UUIDs."""

from dftimewolf.lib import resources
from dftimewolf.lib.validators import regex
from dftimewolf.lib.validators import manager as validators_manager


class UUIDValidator(regex.RegexValidator):
  """Validates a UUID."""

  NAME = "uuid"
  _UUID_REGEX = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

  def ValidateSingle(self,
                     argument_value: str,
                     recipe_argument: resources.RecipeArgument) -> str:
    """Validates a UUID.

    Args:
      argument_value: The UUID to validate.
      recipe_argument: The definition of the argument.

    Returns:
      The validated UUID.
    """
    recipe_argument.validation_params['regex'] = self._UUID_REGEX

    return super().ValidateSingle(argument_value, recipe_argument)


validators_manager.ValidatorsManager.RegisterValidator(UUIDValidator)
