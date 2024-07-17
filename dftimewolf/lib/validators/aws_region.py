# -*- coding: utf-8 -*-
"""Validator for AWS region names."""
from typing import Any
from dftimewolf.lib import errors, resources, args_validator
from dftimewolf.lib.validators import manager as validators_manager

# Source:
#   curl -s https://ip-ranges.amazonaws.com/ip-ranges.json | \
#   jq -r '.prefixes[] | select(.service == "EC2") | .region' ip-ranges.json \
#   | sort | uniq
# Fetched 2023-01-15
# TODO - Fetch at runtime?
REGIONS = frozenset({
    'af-south-1', 'ap-east-1', 'ap-northeast-1', 'ap-northeast-2',
    'ap-northeast-3', 'ap-south-1', 'ap-south-2', 'ap-southeast-1',
    'ap-southeast-2', 'ap-southeast-3', 'ap-southeast-4', 'ap-southeast-6',
    'ca-central-1', 'ca-west-1', 'cn-north-1', 'cn-northwest-1',
    'eu-central-1',
    'eu-central-2', 'eu-north-1', 'eu-south-1', 'eu-south-2', 'eu-west-1',
    'eu-west-2', 'eu-west-3', 'il-central-1', 'me-central-1', 'me-south-1',
    'sa-east-1', 'us-east-1', 'us-east-2', 'us-gov-east-1', 'us-gov-west-1',
    'us-west-1', 'us-west-2'})


class AWSRegionValidator(args_validator.AbstractValidator):
  """Validates a correct AWS region."""

  NAME = 'aws_region'

  def Validate(self,
               argument_value: Any,
               recipe_argument: resources.RecipeArgument) -> str:
    """Validate operand is a valid AWS region.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      A valid AWS region name.

    Raises:
      RecipeArgsValidationFailure: if the argument value is not a valid AWS
        region.
    """
    if argument_value not in REGIONS:
      raise (errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Invalid AWS Region name'))

    return str(argument_value)

validators_manager.ValidatorsManager.RegisterValidator(AWSRegionValidator)
