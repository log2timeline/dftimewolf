# -*- coding: utf-8 -*-
"""Validator for dates and times"""
import datetime

from typing import Any, Union
from dateutil import parser

from dftimewolf.lib import errors, resources, args_validator
from dftimewolf.lib.validators import manager as validators_manager



class DatetimeValidator(args_validator.AbstractValidator):
  """Validates a date and time string.

  Accepts dates in ISO2601 format only.
  """

  NAME = 'datetime'

  def _EnsureTimezone(
      self, parsed_datetime: datetime.datetime) -> datetime.datetime:
    """Ensures that the argument has timezone information.

    If there is no timezone information, the timezone will be set to UTC.

    Args:
      parsed_datetime: Datetime to validate.

    Returns:
      A datetime with timezone information.
    """
    # If there's no timezone information, we assume it is UTC.
    if (parsed_datetime.tzinfo is None or
        parsed_datetime.tzinfo.utcoffset(parsed_datetime) is None):
      parsed_datetime = parsed_datetime.replace(tzinfo=datetime.UTC)
    return parsed_datetime

  def Validate(self, argument_value: Any,
              recipe_argument: resources.RecipeArgument) -> datetime.datetime:
    """Validate that operand is a valid date and time string.

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
    if not isinstance(argument_value, str):
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Argument value must be a string.')

    validation_parameters = recipe_argument.validation_params

    try:
      parsed_datetime = parser.isoparse(argument_value)
      parsed_datetime = self._EnsureTimezone(parsed_datetime)
    except (parser.ParserError, ValueError) as exception:
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          f'is not a valid datetime: {str(exception)}')

    before_value = validation_parameters.get('before')
    try:
      if before_value:
        if not self._ValidateOrder(parsed_datetime, before_value):
          raise errors.RecipeArgsValidationFailure(
              recipe_argument.switch,
              argument_value,
              self.NAME,
              (f'{before_value} is after {parsed_datetime} but it '
               'should be the other way around'))
    except (parser.ParserError, ValueError) as exception:
      raise errors.RecipeArgsValidatorError(
          f'Error in order comparison: {str(exception)}')

    after_value = validation_parameters.get('after')
    try:
      if after_value:
        if not self._ValidateOrder(after_value, parsed_datetime):
          raise errors.RecipeArgsValidationFailure(
              recipe_argument.switch,
              argument_value,
              self.NAME,
              (f'{parsed_datetime} is before {after_value} but it '
               'should be the other way around'))
    except (parser.ParserError, ValueError) as exception:
      raise errors.RecipeArgsValidatorError(
          f'Error in order comparison: {str(exception)}')
    return parsed_datetime

  def _ValidateOrder(self,
      first: Union[str, datetime.datetime],
      second: Union[str, datetime.datetime]) -> bool:
    """Validates date ordering.

    Args:
      first: The intended earlier date.
      second: The intended later date.

    Returns:
      True if the ordering is correct, false otherwise.

    Raises:
      ValueError: If string -> datetime conversion fails.
    """
    first_datetime: datetime.datetime
    second_datetime: datetime.datetime
    if isinstance(first, str):
      first_datetime = parser.isoparse(first)
      first_datetime = self._EnsureTimezone(first_datetime)
    else:
      first_datetime = first
    if isinstance(second, str):
      second_datetime = parser.isoparse(second)
      second_datetime = self._EnsureTimezone(second_datetime)
    else:
      second_datetime = second

    return first_datetime < second_datetime

class EndTimeValidator(DatetimeValidator):
  """A special subclass that sets date times to be the end of day."""

  NAME = 'datetime_end'

  def Validate(self, argument_value: str,
      recipe_argument: resources.RecipeArgument) -> datetime.datetime:
    """Validates a date, and sets the time to 23:59:59 if it's unset.

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
    dt = super().Validate(argument_value, recipe_argument)
    if (dt.hour, dt.minute, dt.second) == (0, 0, 0):
      dt = dt.replace(hour=23, minute=59, second=59)
    return dt


validators_manager.ValidatorsManager.RegisterValidators(
    [DatetimeValidator, EndTimeValidator])
