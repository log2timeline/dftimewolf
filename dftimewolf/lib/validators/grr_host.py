# -*- coding: utf-8 -*-
"""Validator for GRR host identifiers."""
import re
from typing import Any

from dftimewolf.lib import errors, resources
from dftimewolf.lib.validators import hostname
from dftimewolf.lib.validators import manager as validators_manager


class GRRHostValidator(hostname.HostnameValidator):
  """Validates a GRR host identifier.

  GRR can accept FQDNs, or GRR client IDs, which take the form of
  C.1facf5562db006ad.
  """

  NAME = 'grr_host'
  GRR_REGEX = r'^C\.[0-9a-f]{16}$'

  def ValidateSingle(self, argument_value: Any,
      recipe_argument: resources.RecipeArgument) -> str:
    """Validates a GRR host ID.

    Args:
      argument_value: The ID to validate.
      recipe_argument: Unused for this validator.

    Returns:
      A valid GRR host identifier.

    Raises:
      errors.RecipeArgsValidationFailure: If the argument value is not a GRR
        host ID.
    """
    if not isinstance(argument_value, str):
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Argument value must be a string.')

    regexes = [self.GRR_REGEX, self.FQDN_REGEX, self.HOSTNAME_REGEX]

    for regex in regexes:
      if re.match(regex, argument_value):
        return argument_value

    raise errors.RecipeArgsValidationFailure(
        recipe_argument.switch,
        argument_value,
        self.NAME,
        'Not a GRR host identifier')

validators_manager.ValidatorsManager.RegisterValidator(GRRHostValidator)
