# -*- coding: utf-8 -*-
"""Validator for GCP zone names."""
from typing import Any

from dftimewolf.lib import errors, resources
from dftimewolf.lib.args_validator import AbstractValidator
from dftimewolf.lib.validators import manager as validators_manager

# Source: `gcloud compute zones list --format=json | jq -r '.[].name' | sort`
# Fetched 2026-09-21
# TODO - Fetch at runtime?
ZONES = frozenset({
    'africa-south1-a', 'africa-south1-b', 'africa-south1-c', 'asia-east1-a',
    'asia-east1-b', 'asia-east1-c', 'asia-east2-a', 'asia-east2-b',
    'asia-east2-c', 'asia-northeast1-a', 'asia-northeast1-b',
    'asia-northeast1-c', 'asia-northeast2-a', 'asia-northeast2-b',
    'asia-northeast2-c', 'asia-northeast3-a', 'asia-northeast3-b',
    'asia-northeast3-c', 'asia-south1-a', 'asia-south1-b', 'asia-south1-c',
    'asia-south2-a', 'asia-south2-b', 'asia-south2-c', 'asia-southeast1-a',
    'asia-southeast1-b', 'asia-southeast1-c', 'asia-southeast2-a',
    'asia-southeast2-b', 'asia-southeast2-c', 'asia-southeast3-a',
    'asia-southeast3-b', 'asia-southeast3-c', 'australia-southeast1-a',
    'australia-southeast1-b', 'australia-southeast1-c',
    'australia-southeast2-a', 'australia-southeast2-b',
    'australia-southeast2-c', 'europe-central2-a', 'europe-central2-b',
    'europe-central2-c', 'europe-north1-a', 'europe-north1-b',
    'europe-north1-c', 'europe-north2-a', 'europe-north2-b', 'europe-north2-c',
    'europe-southwest1-a', 'europe-southwest1-b', 'europe-southwest1-c',
    'europe-west10-a', 'europe-west10-b', 'europe-west10-c', 'europe-west12-a',
    'europe-west12-b', 'europe-west12-c', 'europe-west15-a', 'europe-west15-b',
    'europe-west15-c', 'europe-west1-b', 'europe-west1-c', 'europe-west1-d',
    'europe-west2-a', 'europe-west2-b', 'europe-west2-c', 'europe-west3-a',
    'europe-west3-b', 'europe-west3-c', 'europe-west4-a', 'europe-west4-b',
    'europe-west4-c', 'europe-west6-a', 'europe-west6-b', 'europe-west6-c',
    'europe-west8-a', 'europe-west8-b', 'europe-west8-c', 'europe-west9-a',
    'europe-west9-b', 'europe-west9-c', 'me-central1-a', 'me-central1-b',
    'me-central1-c', 'me-central2-a', 'me-central2-b', 'me-central2-c',
    'me-west1-a', 'me-west1-b', 'me-west1-c', 'northamerica-northeast1-a',
    'northamerica-northeast1-b', 'northamerica-northeast1-c',
    'northamerica-northeast2-a', 'northamerica-northeast2-b',
    'northamerica-northeast2-c', 'northamerica-south1-a',
    'northamerica-south1-b', 'northamerica-south1-c', 'southamerica-east1-a',
    'southamerica-east1-b', 'southamerica-east1-c', 'southamerica-west1-a',
    'southamerica-west1-b', 'southamerica-west1-c', 'us-central1-a',
    'us-central1-b', 'us-central1-c', 'us-central1-f', 'us-central2-a',
    'us-central2-b', 'us-central2-c', 'us-central2-d', 'us-east1-b',
    'us-east1-c', 'us-east1-d', 'us-east4-a', 'us-east4-b', 'us-east4-c',
    'us-east5-a', 'us-east5-b', 'us-east5-c', 'us-east7-a', 'us-east7-b',
    'us-east7-c', 'us-south1-a', 'us-south1-b', 'us-south1-c', 'us-west1-a',
    'us-west1-b', 'us-west1-c', 'us-west2-a', 'us-west2-b', 'us-west2-c',
    'us-west3-a', 'us-west3-b', 'us-west3-c', 'us-west4-a', 'us-west4-b',
    'us-west4-c', 'us-west8-a', 'us-west8-b', 'us-west8-c', 'global'})


class GCPZoneValidator(AbstractValidator):
  """Validates a GCP zone."""

  NAME = 'gcp_zone'

  def Validate(self,
               argument_value: Any,
               recipe_argument: resources.RecipeArgument) -> str:
    """Validate that argument value is a valid GCP zone.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      A valid GCP zone name.

    Raises:
      RecipeArgsValidationFailure: If the argument is not a valid GCP zone.
    """
    if argument_value not in ZONES:
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Invalid GCP Zone name')

    return str(argument_value)
validators_manager.ValidatorsManager.RegisterValidator(GCPZoneValidator)
