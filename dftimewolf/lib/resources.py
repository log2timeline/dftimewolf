# -*- coding: utf-8 -*-
"""Various dfTimewolf resource objects."""

import dataclasses
from typing import Any, Dict, Sequence


@dataclasses.dataclass
class RecipeArgument:
  """Dataclass for a single recipe argument.

  Attributes:
    switch: name of the argument. An argument name starting with '--' indicates
      that the argument is optional.
    help_text: human-readable description of the argument.
    default: default value of the argument.
    validation_params: format of the argument. Indicates which validator to
      use to validate the argument, as well as any configuration options for
      the validator.
  """
  switch: str = ''
  help_text: str = ''
  default: Any = None
  validation_params: Dict[str, Any] = dataclasses.field(default_factory=dict)


class Recipe(object):
  """Recipe.

  Attributes:
    args (Sequence[RecipeArgument]): command line arguments of
        the recipe.
    contents (dict[str, object]): recipe contents.
    description (str): description.
    name (str): name that identifies the recipe.
  """

  def __init__(self,
               description: str,
               contents: Dict[str, Any],
               args: Sequence[RecipeArgument]) -> None:
    """Initializes a recipe.

    Args:
      description (str): description.
      contents (dict[str, object]): recipe contents.
      args (Sequence[RecipeArgument]): command line arguments of
          the recipe.
    """
    super(Recipe, self).__init__()
    self.args: Sequence[RecipeArgument] = args
    self.contents = contents
    self.name = contents['name']  # type: str
    self.description = description

  def GetHelpString(self) -> str:
    """Generates a description for argparse help.

    Returns:
      str: help text.
    """
    short_description = self.contents.get(
        'short_description', 'No description')
    return ' {0:<35s}{1:s}\n'.format(self.name, short_description)
