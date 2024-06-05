# -*- coding: utf-8 -*-
"""Manager class for validators."""
from typing import Dict, List, Optional, Sequence, Type

from dftimewolf.lib import errors, resources, args_validator


class ValidatorsManager:
  """Class that handles validating arguments."""

  _validator_classes = {}  # type: Dict[str, Type['args_validator.AbstractValidator']] # pylint: disable=line-too-long

  @classmethod
  def ListValidators(cls) -> List[str]:
    """Returns a list of all registered validators.

    Returns:
      A list of all registered validators.
    """
    return list(cls._validator_classes.keys())


  @classmethod
  def RegisterValidator(
      cls, validator_class: Type['args_validator.AbstractValidator']) -> None:
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
  def DeregisterValidator(
      cls,  validator_class: Type['args_validator.AbstractValidator']) -> None:
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
      cls,
      validator_classes: Sequence[Type['args_validator.AbstractValidator']]) -> None: #pylint: disable=line-too-long
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
  def GetValidatorByName(
      cls, name: str) -> Optional[Type['args_validator.AbstractValidator']]:
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
    validator_name = str(recipe_argument.validation_params.get("format", ""))
    if not validator_name:
      return argument_value

    if validator_name not in cls._validator_classes:
      raise errors.RecipeArgsValidatorError(
          f'{validator_name} is not a registered validator')

    validator_class = cls._validator_classes[validator_name]
    validator = validator_class()

    return validator.Validate(argument_value, recipe_argument)
