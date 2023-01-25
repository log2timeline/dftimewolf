"""Validators for recipe arguments."""

import abc
import ipaddress
import re

from typing import Any, Dict, Optional, Callable

from dftimewolf.lib import errors


class AbstractValidator(abc.ABC):
  """Base class for validator objects."""

  name: str = None  # type: ignore

  @abc.abstractmethod
  def __init__(self) -> None:
    """Initialise."""

  @abc.abstractmethod
  def GenerateValidateCallable(self, validator_params: Dict[str, Any]) -> Callable[[str], bool]:
    """Generate the callable that will validate a parameter."""


class DefaultValidator(AbstractValidator):
  """The default validator always returns true."""

  def __init__(self) -> None:
    """Initialise."""
    super().__init__()
    self.name = 'default'

  def GenerateValidateCallable(self) -> Callable[[str], bool]:
    return lambda str: True


class AWSRegionValidator(AbstractValidator):
  """Validates a correct AWS region."""

  # pylint: disable=line-too-long
  # Source:
  #   curl -s https://ip-ranges.amazonaws.com/ip-ranges.json | \
  #   jq -r '.prefixes[] | select(.service == "EC2") | .region' ip-ranges.json \
  #   | sort | uniq
  # Fetched 2023-01-15
  # pylint: enable=line-too-long
  _regions = {  # TODO - Fetch at runtime?
    'af-south-1', 'ap-east-1', 'ap-northeast-1', 'ap-northeast-2',
    'ap-northeast-3', 'ap-south-1', 'ap-south-2', 'ap-southeast-1',
    'ap-southeast-2', 'ap-southeast-3', 'ap-southeast-4', 'ap-southeast-6',
    'ca-central-1', 'ca-west-1', 'cn-north-1', 'cn-northwest-1', 'eu-central-1',
    'eu-central-2', 'eu-north-1', 'eu-south-1', 'eu-south-2', 'eu-west-1',
    'eu-west-2', 'eu-west-3', 'il-central-1', 'me-central-1', 'me-south-1',
    'sa-east-1', 'us-east-1', 'us-east-2', 'us-gov-east-1', 'us-gov-west-1',
    'us-west-1', 'us-west-2'
  }

  def __init__(self) -> None:
    """Initialise."""
    super().__init__()
    self.name = 'aws_region'

  def GenerateValidateCallable(self, validator_params) -> Callable[[str], bool]:
    return self.Validate
    
  def Validate(self, operand):
    if operand not in self._regions:
      raise ValueError('Invalid AWS Region name')
    return operand


class RegexValidator(AbstractValidator):
  """Validates a string according to a regular expression."""

  def __init__(self) -> None:
    """Initialise."""
    super().__init__()
    self.name = 'regex'
    self.regex = ''


  def GenerateValidateCallable(self, validator_params) -> Callable[[str], bool]:
    if 'regex' not in validator_params:
      raise errors.RecipeArgsValidatorError(
          'Missing validator parameter: regex')

    self.regex = re.compile(validator_params['regex'])

    return self.Validate
    
  def Validate(self, operand):
    if not self.regex.match(operand):
      raise ValueError(
          f'"{operand}" does not match regex /{self.regex}/')
    return operand


class DFTWRecipeArgsValidator:
  """Class used for validating recipe argument foramts."""

  def __init__(self) -> None:
    """Init."""
    self._validators: Dict[str, AbstractValidator] = {}
    self._default_validator: AbstractValidator = DefaultValidator()

    self.RegisterValidator(AWSRegionValidator())
#    self.RegisterValidator(GCPZoneValidator())
    self.RegisterValidator(RegexValidator())
#    self.RegisterValidator(SubnetValidator())

  def RegisterValidator(self, validator: AbstractValidator) -> None:
    """Register a validator class for usage."""
    self._validators[validator.name] = validator
    
  def __getitem__(self, key: Optional[str]) -> Callable[[Dict[str, Any]], Callable[[str], bool]]:
    """Square bracket access. Returns a callable that you can then pass a dict
    of params to and get a callable(str) back."""
    if key is None:
      return self._default_validator.GenerateValidateCallable
    if key in self._validators:
      return self._validators[key].GenerateValidateCallable
    else:
      raise errors.RecipeArgsValidatorError(
          f'{key} is not a valid validator name')


