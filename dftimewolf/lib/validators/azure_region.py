# -*- coding: utf-8 -*-
"""Validator for Azure region names."""
from typing import Any

from dftimewolf.lib import errors, resources, args_validator
from dftimewolf.lib.validators import manager as validators_manager

# Source: curl https://datacenters.microsoft.com/wp-json/globe/regions | \
#   jq -r '.[].id' | sort | uniq
# Fetched 2026-09-21
# TODO - Fetch at runtime?
REGIONS = frozenset({
    'australiacentral', 'australiaeast', 'australiasoutheast', 'austriaeast',
    'belgiumcentral', 'brazilsouth', 'canadacentral', 'canadaeast',
    'centralindia', 'centralus', 'chilecentral', 'chinaeast2', 'chinanorth2',
    'chinanorth3', 'denmark-north-europe-4', 'denmarkeast', 'eastasia',
    'eastus', 'eastus2', 'eastus3', 'francecentral', 'germanywestcentral',
    'greececentral', 'indonesiacentral', 'israelcentral', 'italynorth',
    'japaneast', 'japanwest', 'koreacentral', 'malaysiawest', 'mexicocentral',
    'newzealandnorth', 'northcentralus', 'northeurope', 'northeurope3',
    'norwayeast', 'polandcentral', 'qatarcentral', 'saudiarabiaeast',
    'southafricanorth', 'southcentralindia', 'southcentralus',
    'southeast-asia-3', 'southeastasia', 'southindia', 'spaincentral',
    'swedencentral', 'switzerlandnorth', 'taiwannorth', 'thailand-south',
    'uaenorth', 'uksouth', 'ukwest', 'westcentralus', 'westeurope', 'westus',
    'westus2', 'westus3'})


class AzureRegionValidator(args_validator.AbstractValidator):
  """Validates an Azure region."""

  NAME = 'azure_region'

  def Validate(self,
               argument_value: Any,
               recipe_argument: resources.RecipeArgument) -> str:
    """Validate that argument is a valid Azure region.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      A valid Azure region name.

    Raises:
      RecipeArgsValidationFailure: If the argument value is not a valid Azure
        region.
    """
    if argument_value not in REGIONS:
      raise (errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Invalid Azure Region name'))

    return str(argument_value)

validators_manager.ValidatorsManager.RegisterValidator(AzureRegionValidator)
