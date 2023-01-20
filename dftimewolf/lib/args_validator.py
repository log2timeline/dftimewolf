"""Validators for recipe arguments."""

import abc
import ipaddress
import re

from typing import Any, Dict, Optional

from dftimewolf.lib import errors


class AbstractValidator(abc.ABC):
  """Base class for validator objects."""

  name: str = None  # type: ignore

  @abc.abstractmethod
  def __init__(self) -> None:
    """Initialise."""

  @abc.abstractmethod
  def Validate(
      self, operand: Any, validator_params: Optional[Dict[str, Any]]) -> None:
    """Validate the parameter.

    Subclasses that override this should raise errors.RecipeArgsValidatorError
    on validation failures, with a string describing the problem."""


class CommaSeparatedValidator(AbstractValidator):
  """Subclass of AbstractValidator that allows for comma separated strings.

  Subclasses that override this should implement ValidateSingle instead of
  Validate."""

  def Validate(self,
               operand: str,
               validator_params: Dict[str, Any]) -> None:
    """Split the string by commas if validator_params['comma_separated'] == True
    and validate each component in ValidateSingle."""

    if 'comma_separated' not in validator_params:
      raise errors.RecipeArgsValidatorError(
          'Missing validator parameter: comma_separated')

    operands = []
    if validator_params['comma_separated']:
      operands = operand.split(',')
    else:
      operands.append(operand)

    for op in operands:
      self.ValidateSingle(op, validator_params)

  @abc.abstractmethod
  def ValidateSingle(
      self, operand: str, validator_params: Optional[Dict[str, Any]]) -> None:
    """Validate a single operand from a comma separated list."""


class DefaultValidator(AbstractValidator):
  """The default validator always returns true."""

  def __init__(self) -> None:
    """Initialise."""
    super().__init__()
    self.name = 'default'

  def Validate(self,
               operand: Any,
               validator_params: Optional[Dict[str, Any]]) -> None:
    """Never raises an errors.RecipeArgsValidatorError."""


class AWSRegionValidator(AbstractValidator):
  """Validates a correct AWS region."""

  # pylint: disable=line-too-long
  # Source: curl -s https://ip-ranges.amazonaws.com/ip-ranges.json | jq -r '.prefixes[] | select(.service == "EC2") | .region' ip-ranges.json  | sort | uniq
  # Fetched 2023-01-15
  # pylint: enable=line-too-long
  _regions = [
    'af-south-1', 'ap-east-1', 'ap-northeast-1', 'ap-northeast-2',
    'ap-northeast-3', 'ap-south-1', 'ap-south-2', 'ap-southeast-1',
    'ap-southeast-2', 'ap-southeast-3', 'ap-southeast-4', 'ap-southeast-6',
    'ca-central-1', 'ca-west-1', 'cn-north-1', 'cn-northwest-1', 'eu-central-1',
    'eu-central-2', 'eu-north-1', 'eu-south-1', 'eu-south-2', 'eu-west-1',
    'eu-west-2', 'eu-west-3', 'il-central-1', 'me-central-1', 'me-south-1',
    'sa-east-1', 'us-east-1', 'us-east-2', 'us-gov-east-1', 'us-gov-west-1',
    'us-west-1', 'us-west-2'
  ]

  def __init__(self) -> None:
    """Initialise."""
    super().__init__()
    self.name = 'aws_region'

  def Validate(self,
               operand: Any,
               validator_params: Dict[str, Any]) -> None:
    """Validate operand is a valid AWS region."""
    if operand not in self._regions:
      raise errors.RecipeArgsValidatorError('Invalid AWS Region name')


class GCPZoneValidator(AbstractValidator):
  """Validates a correct GCP zone."""

  # Source: https://cloud.google.com/compute/docs/regions-zones/
  # Fetched 2023-01-13
  _zones = [
    'asia-east1-a', 'asia-east1-b', 'asia-east1-c', 'asia-east2-a',
    'asia-east2-b', 'asia-east2-c', 'asia-northeast1-a', 'asia-northeast1-b',
    'asia-northeast1-c', 'asia-northeast2-a', 'asia-northeast2-b',
    'asia-northeast2-c', 'asia-northeast3-a', 'asia-northeast3-b',
    'asia-northeast3-c', 'asia-south1-a', 'asia-south1-b', 'asia-south1-c',
    'asia-south2-a', 'asia-south2-b', 'asia-south2-c', 'asia-southeast1-a',
    'asia-southeast1-b', 'asia-southeast1-c', 'asia-southeast2-a',
    'asia-southeast2-b', 'asia-southeast2-c', 'australia-southeast1-a',
    'australia-southeast1-b', 'australia-southeast1-c',
    'australia-southeast2-a', 'australia-southeast2-b',
    'australia-southeast2-c', 'europe-central2-a', 'europe-central2-b',
    'europe-central2-c', 'europe-north1-a', 'europe-north1-b',
    'europe-north1-c',     'europe-southwest1-a', 'europe-southwest1-b',
    'europe-southwest1-c', 'europe-west1-b', 'europe-west1-c',
    'europe-west1-d', 'europe-west2-a', 'europe-west2-b', 'europe-west2-c',
    'europe-west3-a', 'europe-west3-b', 'europe-west3-c', 'europe-west4-a',
    'europe-west4-b', 'europe-west4-c', 'europe-west6-a', 'europe-west6-b',
    'europe-west6-c', 'europe-west8-a', 'europe-west8-b', 'europe-west8-c',
    'europe-west9-a', 'europe-west9-b', 'europe-west9-c', 'me-west1-a',
    'me-west1-b', 'me-west1-c', 'northamerica-northeast1-a',
    'northamerica-northeast1-b', 'northamerica-northeast1-c',
    'northamerica-northeast2-a', 'northamerica-northeast2-b',
    'northamerica-northeast2-c', 'southamerica-east1-a', 'southamerica-east1-b',
    'southamerica-east1-c', 'southamerica-west1-a', 'southamerica-west1-b',
    'southamerica-west1-c', 'us-central1-a', 'us-central1-b', 'us-central1-c',
    'us-central1-f', 'us-east1-b', 'us-east1-c', 'us-east1-d', 'us-east4-a',
    'us-east4-b', 'us-east4-c', 'us-east5-a', 'us-east5-b', 'us-east5-c',
    'us-south1-a', 'us-south1-b', 'us-south1-c', 'us-west1-a', 'us-west1-b',
    'us-west1-c', 'us-west2-a', 'us-west2-b', 'us-west2-c', 'us-west3-a',
    'us-west3-b', 'us-west3-c', 'us-west4-a', 'us-west4-b', 'us-west4-c']

  def __init__(self) -> None:
    """Initialise."""
    super().__init__()
    self.name = 'gcp_zone'

  def Validate(self,
               operand: Any,
               validator_params: Optional[Dict[str, Any]]) -> None:
    """Validate that operand is a valid GCP zone."""
    if operand not in self._zones:
      raise errors.RecipeArgsValidatorError('Invalid GCP zone name')


class RegexValidator(CommaSeparatedValidator):
  """Validates a string according to a regular expression."""

  def __init__(self) -> None:
    """Initialise."""
    super().__init__()
    self.name = 'regex'

  def ValidateSingle(self,
                     operand: str,
                     validator_params: Dict[str, Any]) -> None:
    """Validate a string according to a regular expression."""
    if 'regex' not in validator_params:
      raise errors.RecipeArgsValidatorError(
          'Missing validator parameter: regex')

    regex = re.compile(validator_params['regex'])
    if not regex.match(operand):
      raise errors.RecipeArgsValidatorError(
          f'"{operand}" does not match regex /{validator_params["regex"]}/')


class SubnetValidator(CommaSeparatedValidator):
  """Validates a subnet."""
  def __init__(self) -> None:
    """Initialise."""
    super().__init__()
    self.name = 'subnet'

  def ValidateSingle(self,
                     operand: str,
                     validator_params: Optional[Dict[str, Any]]) -> None:
    """Validate that operand is a valid subnet string."""
    try:
      ipaddress.ip_network(operand)
    except ValueError:
      raise errors.RecipeArgsValidatorError(f'{operand} is not a valid subnet.')


class ValidatorManager:
  """Class that handles validating arguments."""

  def __init__(self) -> None:
    """Initialise."""
    self._validators: Dict[str, AbstractValidator] = {}
    self._default_validator: AbstractValidator = DefaultValidator()

    self.RegisterValidator(AWSRegionValidator())
    self.RegisterValidator(GCPZoneValidator())
    self.RegisterValidator(RegexValidator())
    self.RegisterValidator(SubnetValidator())

  def RegisterValidator(self, validator: AbstractValidator) -> None:
    """Register a validator class for usage."""
    self._validators[validator.name] = validator

  def Validate(self,
               operand: Any,
               validator_params: Optional[Dict[str, Any]]=None) -> None:
    """Validate a operand."""
    if validator_params is None:
      validator = self._default_validator
    else:
      if validator_params['format'] not in self._validators:
        raise errors.RecipeArgsValidatorError(
            f'{validator_params["format"]} is not a valid validator name')

      validator = self._validators.get(
          validator_params['format'], self._default_validator)

    validator.Validate(operand, validator_params)
