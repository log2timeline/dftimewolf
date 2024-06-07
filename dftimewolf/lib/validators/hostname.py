# -*- coding: utf-8 -*-
"""Validator for hostnames."""
import re

from dftimewolf.lib import errors, resources, args_validator
from dftimewolf.lib.validators import manager as validators_manager


class HostnameValidator(args_validator.CommaSeparatedValidator):
  """Validator for hostnames.

  Can validate flat hostnames and FQDNs. Optionally, can have `fqdn_only`
  specified to require FQDNs and reject flat hostnames."""

  NAME = 'hostname'
  FQDN_ONLY_FLAG = 'fqdn_only'
  HOSTNAME_REGEX = r'^[-_a-z0-9]{3,64}$'  # Flat names, like 'localhost'
  FQDN_REGEX = (
      r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)')

  # Source: https://stackoverflow.com/questions/11809631/fully-qualified-domain-name-validation#20204811  # pylint: disable=line-too-long
  # Retrieved 2023-02-03

  def ValidateSingle(self, argument_value: str,
      recipe_argument: resources.RecipeArgument) -> str:
    """Validate a hostname.

    Args:
      argument_value: The hostname to validate.
      recipe_argument: The definition of the argument.

    Returns:
      A valid hostname.

    Raises:
      errors.RecipeArgsValidationFailure: If the argument is not a valid hostname.
    """
    regexes = [self.FQDN_REGEX]
    if not recipe_argument.validation_params.get(self.FQDN_ONLY_FLAG, False):
      regexes.append(self.HOSTNAME_REGEX)

    for regex in regexes:
      if re.match(regex, argument_value):
        return argument_value

    raise errors.RecipeArgsValidationFailure(
        recipe_argument.switch,
        argument_value,
        self.NAME,
        'Not a valid hostname')

validators_manager.ValidatorsManager.RegisterValidator(HostnameValidator)
