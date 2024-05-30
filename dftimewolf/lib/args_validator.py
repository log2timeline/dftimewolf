"""Validators for recipe arguments."""

import abc
import ipaddress
import re

from typing import Any, Dict, List, Union, Type, Sequence, Optional

import datetime
from urllib.parse import urlparse

from dftimewolf.lib import errors, resources


class AbstractValidator(abc.ABC):
  """Base class for validator objects."""

  NAME: str = None  # type: ignore

  def __init__(self) -> None:
    """Initialize."""

  @abc.abstractmethod
  def Validate(self,
               argument_value: str,
               recipe_argument: resources.RecipeArgument) -> str:
    """Validates an argument value.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      A valid version of the argument value.

    Raises:
      errors.RecipeArgsValidationFailure: An error in validation.
      errors.RecipeArgsValidatorError: An error in validation.
    """


class CommaSeparatedValidator(AbstractValidator):
  """Validator for comma separated strings.

  Subclasses that override this should implement ValidateSingle instead of
  Validate."""

  def Validate(self,
               argument_value: str,
               recipe_argument: resources.RecipeArgument) -> str:
    """Split the string by commas if validator_params['comma_separated'] == True
    and validate each component in ValidateSingle.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      A validated version of the parameter.

    Raises:
      errors.RecipeArgsValidationFailure: If an invalid argument is found.
      errors.RecipeArgsValidatorError: An error in validation.
    """
    validation_params = recipe_argument.validation_params
    if 'comma_separated' not in validation_params:
      validation_params['comma_separated'] = False

    arguments = []
    if validation_params['comma_separated']:
      arguments = argument_value.split(',')
    else:
      arguments.append(argument_value)

    valid_arguments = [
        self.ValidateSingle(item, recipe_argument) for item in arguments]
    argument_string = ','.join(valid_arguments)

    return argument_string

  @abc.abstractmethod
  def ValidateSingle(self,
                     argument_value: str,
                     recipe_argument: resources.RecipeArgument) -> str:
    """Validate a single operand from a comma separated list.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      object: a validated version of the parameter.

    Raises:
      errors.RecipeArgsValidationFailure: If an invalid argument is found.
      errors.RecipeArgsValidatorError: An error in validation.
    """


class AWSRegionValidator(AbstractValidator):
  """Validates a correct AWS region."""

  # Source:
  #   curl -s https://ip-ranges.amazonaws.com/ip-ranges.json | \
  #   jq -r '.prefixes[] | select(.service == "EC2") | .region' ip-ranges.json \
  #   | sort | uniq
  # Fetched 2023-01-15
  # TODO - Fetch at runtime?
  _regions = {
      'af-south-1', 'ap-east-1', 'ap-northeast-1', 'ap-northeast-2',
      'ap-northeast-3', 'ap-south-1', 'ap-south-2', 'ap-southeast-1',
      'ap-southeast-2', 'ap-southeast-3', 'ap-southeast-4', 'ap-southeast-6',
      'ca-central-1', 'ca-west-1', 'cn-north-1', 'cn-northwest-1',
      'eu-central-1',
      'eu-central-2', 'eu-north-1', 'eu-south-1', 'eu-south-2', 'eu-west-1',
      'eu-west-2', 'eu-west-3', 'il-central-1', 'me-central-1', 'me-south-1',
      'sa-east-1', 'us-east-1', 'us-east-2', 'us-gov-east-1', 'us-gov-west-1',
      'us-west-1', 'us-west-2'
  }
  NAME = 'aws_region'

  def Validate(self,
               argument_value: str,
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
    if argument_value not in self._regions:
      raise (errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Invalid AWS Region name'))

    return argument_value


class AzureRegionValidator(AbstractValidator):
  """Validates an Azure region."""

  # Source: az account list-locations | jq -r '.[].name' | sort
  # Fetched 2023-02-07
  # TODO - Fetch at runtime?
  _regions = {
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
      'westus2stage', 'westus3', 'westusstage'
  }
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
    if argument_value not in self._regions:
      raise (errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Invalid Azure Region name'))

    return argument_value


class GCPZoneValidator(AbstractValidator):
  """Validates a GCP zone."""

  # Source: https://cloud.google.com/compute/docs/regions-zones/
  # Fetched 2023-01-13
  # TODO - Fetch at runtime?
  _zones = {
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
      'europe-north1-c', 'europe-southwest1-a', 'europe-southwest1-b',
      'europe-southwest1-c', 'europe-west1-b', 'europe-west1-c',
      'europe-west1-d', 'europe-west2-a', 'europe-west2-b', 'europe-west2-c',
      'europe-west3-a', 'europe-west3-b', 'europe-west3-c', 'europe-west4-a',
      'europe-west4-b', 'europe-west4-c', 'europe-west6-a', 'europe-west6-b',
      'europe-west6-c', 'europe-west8-a', 'europe-west8-b', 'europe-west8-c',
      'europe-west9-a', 'europe-west9-b', 'europe-west9-c', 'me-west1-a',
      'me-west1-b', 'me-west1-c', 'northamerica-northeast1-a',
      'northamerica-northeast1-b', 'northamerica-northeast1-c',
      'northamerica-northeast2-a', 'northamerica-northeast2-b',
      'northamerica-northeast2-c', 'southamerica-east1-a',
      'southamerica-east1-b',
      'southamerica-east1-c', 'southamerica-west1-a', 'southamerica-west1-b',
      'southamerica-west1-c', 'us-central1-a', 'us-central1-b', 'us-central1-c',
      'us-central1-f', 'us-east1-b', 'us-east1-c', 'us-east1-d', 'us-east4-a',
      'us-east4-b', 'us-east4-c', 'us-east5-a', 'us-east5-b', 'us-east5-c',
      'us-south1-a', 'us-south1-b', 'us-south1-c', 'us-west1-a', 'us-west1-b',
      'us-west1-c', 'us-west2-a', 'us-west2-b', 'us-west2-c', 'us-west3-a',
      'us-west3-b', 'us-west3-c', 'us-west4-a', 'us-west4-b', 'us-west4-c',
      'global'
  }
  NAME = 'gcp_zone'

  def Validate(self,
               argument_value: str,
               recipe_argument: resources.RecipeArgument) -> Any:
    """Validate that operand is a valid GCP zone.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      A valid GCP zone name.

    Raises:
      RecipeArgsValidationFailure: If the argument is not a valid GCP zone.
    """
    if argument_value not in self._zones:
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Invalid GCP Zone name')

    return argument_value


class RegexValidator(CommaSeparatedValidator):
  """Validates a string according to a regular expression."""

  NAME = 'regex'

  def ValidateSingle(self,
                     argument_value: str,
                     recipe_argument: resources.RecipeArgument) -> str:
    """Validate a string according to a regular expression.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      str: a valid string.

    Raises:
      errors.RecipeArgsValidatorError: If no regex is found to use.
      errors.RecipeArgsValidationFailure: If the argument value does not match
        the regex.
    """
    expression = recipe_argument.validation_params.get('regex')
    if expression is None:
      raise errors.RecipeArgsValidatorError(
          'Missing validator parameter: regex')

    regex = re.compile(expression)

    if not regex.match(argument_value):
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          f'does not match regex /{expression}/')

    return argument_value


class SubnetValidator(CommaSeparatedValidator):
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


class DatetimeValidator(AbstractValidator):
  """Validates a datetime string.

  Requires a format string that defines what the datetime should look like.

  Optionally, it can confirm order of multiple dates as well. A recipe can
  specify the following datetime validator:

  {
    "format": "datetime",
    "format_string": "%Y-%m-%dT%H:%M:%SZ",
    "before": "dateX",  # optional
    "after": "dateY"  # optional
  }

  The argument will then be checked that it is before the date in 'before', and
  after the date in 'after'. Caveat: if a value in before or after is also a
  parameter, e.g. with a recipe containing:

  "args": {
    [
      "start_date",
      "Start date",
      null,
      {
        "format": "datetime",
        "format_string": "%Y-%m-%dT%H:%M:%SZ",
        "before": "@end_date"
      }
    ], [
      "end_date",
      "End date",
      null,
      {
        "format": "datetime",
        "format_string": "%Y-%m-%dT%H:%M:%SZ",
        "after": "@start_date"
      }
    ],
    ...
  then "format_string" must be the same for both args.
  """

  NAME = 'datetime'

  def Validate(self, argument_value: str,
      recipe_argument: resources.RecipeArgument) -> str:
    """Validate that operand is a valid GCP zone.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      A valid datetime string.

    Raises:
      errors.RecipeArgsValidatorError: An error in validation.
      errors.RecipeArgsValidationFailure: If the argument is not a valid
        datetime.
    """
    validation_parameters = recipe_argument.validation_params
    if 'format_string' not in validation_parameters:
      raise errors.RecipeArgsValidatorError(
          'Missing validator parameter: format_string')

    try:
      dt = datetime.datetime.strptime(
          argument_value, validation_parameters['format_string'])
    except ValueError:  # Date parsing failure
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          f'does not match format {validation_parameters["format_string"]}')

    try:
      if 'before' in validation_parameters and validation_parameters['before']:
        if not self._ValidateOrder(
            dt, validation_parameters['before'],
            validation_parameters["format_string"]):
          raise errors.RecipeArgsValidationFailure(
              recipe_argument.switch,
              argument_value,
              self.NAME,
              (f'{validation_parameters["before"]} is before {dt} but it '
               'should be the other way around'))

      if 'after' in validation_parameters and validation_parameters['after']:
        if not self._ValidateOrder(
            validation_parameters['after'], dt,
            validation_parameters["format_string"]):
          raise errors.RecipeArgsValidationFailure(
              recipe_argument.switch,
              argument_value,
              self.NAME,
              (f'{dt} is before {validation_parameters["after"]} but it '
               'should be the other way around'))
    except ValueError as exception:
      raise errors.RecipeArgsValidatorError(
          f'Error in order comparison: {str(exception)}')
    return argument_value

  def _ValidateOrder(self,
      first: Union[str, datetime.datetime],
      second: Union[str, datetime.datetime],
      format_string: str) -> bool:
    """Validates date ordering.

    Args:
      first: The intended earlier date.
      second: The intended later date.
      format_string: A format string defining str -> datetime conversion.

    Returns:
      True if the ordering is correct, false otherwise.

    Raises:
      ValueError: If string -> datetime conversion fails.
    """
    if isinstance(first, str):
      first = datetime.datetime.strptime(first, format_string)
    if isinstance(second, str):
      second = datetime.datetime.strptime(second, format_string)

    return first < second


class HostnameValidator(CommaSeparatedValidator):
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


class GRRHostValidator(HostnameValidator):
  """Validates a GRR host identifier.

  GRR can accept FQDNs, or GRR client IDs, which take the form of
  C.1facf5562db006ad.
  """

  NAME = 'grr_host'
  GRR_REGEX = r'^C\.[0-9a-f]{16}$'

  def ValidateSingle(self, argument_value: str,
      recipe_argument: resources.RecipeArgument) -> Any:
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
    regexes = [self.GRR_REGEX, self.FQDN_REGEX, self.HOSTNAME_REGEX]

    for regex in regexes:
      if re.match(regex, argument_value):
        return argument_value

    raise errors.RecipeArgsValidationFailure(
        recipe_argument.switch,
        argument_value,
        self.NAME,
        'Not a GRR host identifier')


class URLValidator(CommaSeparatedValidator):
  """Validates a URL."""

  NAME = "url"

  def ValidateSingle(self,
                     argument_value: str,
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
    url = urlparse(argument_value)
    if not all([url.scheme, url.netloc]):
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Not a valid URL')

    return argument_value


class ValidatorsManager:
  """Class that handles validating arguments."""

  _validator_classes = {}  # type: Dict[str, Type['AbstractValidator']]

  @classmethod
  def ListValidators(cls) -> List[str]:
    """Returns a list of all registered validators.

    Returns:
      A list of all registered validators.
    """
    return list(cls._validator_classes.keys())


  @classmethod
  def RegisterValidator(cls,
                        validator_class: Type['AbstractValidator']) -> None:
    """Register a validator class for usage.

    Args:
      validator_class: Class to register.

    Raises:
      KeyError: if there's already a validator class set for the corresponding
        class name.
    """
    class_name = validator_class.NAME
    if class_name in cls._validator_classes:
      raise KeyError(
          'Validator class already set for: {0:s}.'.format(class_name))

    cls._validator_classes[class_name] = validator_class

  @classmethod
  def DeregisterValidator(cls,
                          validator_class: Type['AbstractValidator']) -> None:
    """Deregister a validator class.

    Args:
      validator_class: Class to deregister.

    Raises:
      KeyError: if validator class is not set for the corresponding class name.
    """
    class_name = validator_class.NAME
    if class_name not in cls._validator_classes:
      raise KeyError('Module class not set for: {0:s}.'.format(class_name))

    del cls._validator_classes[class_name]

  @classmethod
  def RegisterValidators(
      cls, validator_classes: Sequence[Type['AbstractValidator']]) -> None:
    """Registers validator classes.

    The module classes are identified based on their class name.

    Args:
      validator_classes (Sequence[type]): classes to register.
    Raises:
      KeyError: if module class is already set for the corresponding class name.
    """
    for module_class in validator_classes:
      cls.RegisterValidator(module_class)

  @classmethod
  def GetValidatorByName(cls, name: str) -> Optional[Type['AbstractValidator']]:
    """Retrieves a specific validator by its name.

    Args:
      name (str): name of the module.

    Returns:
      type: the module class, which is a subclass of BaseModule, or None if
          no corresponding module was found.
    """
    return cls._validator_classes.get(name, None)

  @classmethod
  def Validate(cls,
               argument_value: str,
               recipe_argument: resources.RecipeArgument) -> str:
    """Validate an argument value.

    Args:
      argument_value: The argument value to validate.
      recipe_argument: The definition of the argument.

    Returns:
      The validated argument value. If the recipe argument doesn't specify a
      validator, the argument value is returned unchanged.

    Raises:
      errors.RecipeArgsValidationFailure: If the argument is not valid.
      errors.RecipeArgsValidatorError: Raised on validator config errors.
    """
    validator_name = recipe_argument.validation_params.get('format', '')
    if not validator_name:
      return argument_value

    if validator_name not in cls._validator_classes:
      raise errors.RecipeArgsValidatorError(
          f'{validator_name} is not a registered validator')

    validator_class = cls._validator_classes[validator_name]
    validator = validator_class()

    return validator.Validate(argument_value, recipe_argument)


ValidatorsManager.RegisterValidators(
    [AWSRegionValidator, AzureRegionValidator, DatetimeValidator,
        HostnameValidator, GCPZoneValidator, GRRHostValidator, RegexValidator,
        SubnetValidator, URLValidator])
