# -*- coding: utf-8 -*-
"""Various dfTimewolf resource objects."""
from typing import Any, Dict, List, Tuple


class Recipe(object):
  """Recipe.

  Attributes:
    args (list[tuple[str, str, object]]): command line arguments of
        the recipe.
    contents (dict[str, object]): recipe contents.
    description (str): description.
    name (str): name that identifies the recipe.
  """

  def __init__(self,
               description: str,
               contents: Dict[str, Any],
               args: List[Tuple[str, str, Any]]) -> None:
    """Initializes a recipe.

    Args:
      description (str): description.
      contents (dict[str, object]): recipe contents.
      args (list[tuple[str, str, object]]): command line arguments of
          the recipe.
    """
    super(Recipe, self).__init__()
    self.args = args
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
