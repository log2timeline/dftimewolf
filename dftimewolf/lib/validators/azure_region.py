# -*- coding: utf-8 -*-
"""Validator for Azure region names."""
from dftimewolf.lib import errors, resources, args_validator
from dftimewolf.lib.validators import manager as validators_manager

# Source: az account list-locations | jq -r '.[].name' | sort
# Fetched 2023-02-07
# TODO - Fetch at runtime?
REGIONS = frozenset({
    'asia', 'asiapacific', 'australia', 'australiacentral',
    'australiacentral2', 'australiaeast', 'australiasoutheast', 'brazil',
    'brazilsouth', 'brazilsoutheast', 'canada', 'canadacentral', 'canadaeast',
    'centralindia', 'centralus', 'centraluseuap', 'centralusstage',
    'eastasia', 'eastasiastage', 'eastus', 'eastus2', 'eastus2euap',
    'eastus2stage', 'eastusstage', 'eastusstg', 'europe', 'france',
    'francecentral', 'francesouth', 'germany', 'germanynorth',
    'germanywestcentral', 'global', 'india', 'japan', 'japaneast',
    'japanwest', 'jioindiacentral', 'jioindiawest', 'korea', 'koreacentral',
    'koreasouth', 'northcentralus', 'northcentralusstage', 'northeurope',
    'norway', 'norwayeast', 'norwaywest', 'qatarcentral', 'singapore',
    'southafrica', 'southafricanorth', 'southafricawest', 'southcentralus',
    'southcentralusstage', 'southcentralusstg', 'southeastasia',
    'southeastasiastage', 'southindia', 'swedencentral', 'switzerland',
    'switzerlandnorth', 'switzerlandwest', 'uae', 'uaecentral', 'uaenorth',
    'uk', 'uksouth', 'ukwest', 'unitedstates', 'unitedstateseuap',
    'westcentralus', 'westeurope', 'westindia', 'westus', 'westus2',
    'westus2stage', 'westus3', 'westusstage'})


class AzureRegionValidator(args_validator.AbstractValidator):
  """Validates an Azure region."""

  NAME = 'azure_region'

  def Validate(self,
               argument_value: str,
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

    return argument_value

validators_manager.ValidatorsManager.RegisterValidator(AzureRegionValidator)
