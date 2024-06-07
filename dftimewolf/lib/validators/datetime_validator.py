# -*- coding: utf-8 -*-
"""Validator for dates and times"""
import datetime
from typing import Union

from dftimewolf.lib import errors, resources, args_validator
from dftimewolf.lib.validators import manager as validators_manager



class DatetimeValidator(args_validator.AbstractValidator):
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

validators_manager.ValidatorsManager.RegisterValidator(DatetimeValidator)
