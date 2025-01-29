"""Validators for recipe arguments."""

import abc

from typing import Any

from dftimewolf.lib import errors, resources


class AbstractValidator(abc.ABC):
  """Base class for validator objects."""

  NAME: str = None  # type: ignore

  def __init__(self, dry_run: bool=False) -> None:
    """Initialize.

    Args:
      dry_run: True if the tool is only testing parameters, False otherwise.
    """
    self._dry_run = dry_run

  @abc.abstractmethod
  def Validate(self,
               argument_value: Any,
               recipe_argument: resources.RecipeArgument) -> Any:
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
               argument_value: Any,
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
    if not isinstance(argument_value, str):
      raise errors.RecipeArgsValidationFailure(
          recipe_argument.switch,
          argument_value,
          self.NAME,
          'Argument value must be a string.')
    validation_params = recipe_argument.validation_params
    if "comma_separated" not in validation_params:
      validation_params["comma_separated"] = False

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
