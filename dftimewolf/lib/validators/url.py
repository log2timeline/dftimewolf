# -*- coding: utf-8 -*-
"""Validator for URLs."""
from typing import Any

from urllib.parse import urlparse

from dftimewolf.lib import errors, resources, args_validator
from dftimewolf.lib.validators import manager as validators_manager


class URLValidator(args_validator.CommaSeparatedValidator):
  """Validates a URL."""

  NAME = "url"

  def ValidateSingle(self,
                     argument_value: Any,
                     recipe_argument: resources.RecipeArgument) -> str:
    """Validates a URL.

    Args:
      argument_value: The URL to validate.
      recipe_argument: The definition of the argument.


    Returns:
      A valid URL string.

    Raises:
      errors.RecipeArgsValidationFailure: If the argument is not a valid URL.
    """
    if not isinstance(argument_value, str):
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Argument value must be a string.')

    url = urlparse(argument_value)
    if not all([url.scheme, url.netloc]):
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Not a valid URL')

    return argument_value

validators_manager.ValidatorsManager.RegisterValidator(URLValidator)
