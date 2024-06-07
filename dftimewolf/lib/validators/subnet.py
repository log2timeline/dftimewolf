# -*- coding: utf-8 -*-
"""Validator for subnets."""
import ipaddress

from dftimewolf.lib import errors, resources, args_validator
from dftimewolf.lib.validators import manager as validators_manager


class SubnetValidator(args_validator.CommaSeparatedValidator):
  """Validates a subnet."""

  NAME = 'subnet'

  def ValidateSingle(self,
                     argument_value: str,
                     recipe_argument: resources.RecipeArgument) -> str:
    """Validate that the argument_value is a valid subnet string.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      A valid subnet string

    Raises:
      errors.RecipeArgsValidationFailure: If the argument is not a valid subnet.
    """
    try:
      ipaddress.ip_network(argument_value)
    except ValueError:
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Not a valid subnet')

    return argument_value

validators_manager.ValidatorsManager.RegisterValidator(SubnetValidator)
