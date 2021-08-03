#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Metawolf utilities."""

import json
import os
import sys
import uuid

from pydoc import locate
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from dftimewolf.lib import errors
from dftimewolf.cli import dftimewolf_recipes
from dftimewolf.metawolf import session
from dftimewolf.lib import resources

if TYPE_CHECKING:
  from dftimewolf.metawolf import output  # pylint: disable=cyclic-import

DFTIMEWOLF = 'dftimewolf'

LAST_ACTIVE_SESSION = 'last_active_session'
LAST_ACTIVE_RECIPE = 'last_active_recipe'
LAST_ACTIVE_PROCESSES = 'last_active_processes'
SESSION_ID_SETTABLE = 'session_id'


class MetawolfUtils:
  """MetawolfUtils holds a set of utility methods for Metawolf.

  Attributes:
    recipe_manager (RecipeManager): A DFTimewolf RecipeManager object.
  """

  def __init__(self, session_path: str = '') -> None:
    """Initialize Metawolf utilities.

    Args:
      session_path (str): Optional. The path to the file in which session
          information should be stored.
    """
    self.session_path = session_path
    self.recipe_manager = self.GetDFTool().RecipeManager()

  @staticmethod
  def GetDFTool() -> dftimewolf_recipes.DFTimewolfTool:
    """Get a DFTimewolfTool object."""
    tool = dftimewolf_recipes.DFTimewolfTool()
    tool.LoadConfiguration()
    try:
      tool.ReadRecipes()
    except KeyError:
      # Recipe already loaded
      pass
    except (errors.RecipeParseError,
            errors.CriticalError) as exception:
      print(exception)
      sys.exit(1)
    return tool

  @staticmethod
  def CreateNewSessionID() -> str:
    """Create a new session ID.

    Returns:
      str: The session ID.
    """
    return uuid.uuid4().hex[:6]

  @staticmethod
  def IsInt(value: str) -> bool:
    """Check if a string can be safely casted to an int.

    Args:
      value (str): The string to check.

    Returns:
      bool: True if the string can be casted to an int.
    """
    try:
      _ = int(value)
    except ValueError:
      return False
    return True

  @staticmethod
  def IsFloat(value: str) -> bool:
    """Check if a string can be safely casted to a float.

    Args:
      value (str): The string to check.

    Returns:
      bool: True if the string can be casted to a float.
    """
    try:
      _ = float(value)
    except ValueError:
      return False
    return True

  @staticmethod
  def Str2Bool(value: str) -> Optional[bool]:
    """Convert a string to its boolean representation.

    Args:
      value (str): The value to convert to a boolean.

    Returns:
      Optional[bool]: True/False if the string can be associated to a boolean,
          None otherwise.
    """
    if not isinstance(value, str):
      return None
    true_set = {'yes', 'true', 't', 'y'}
    false_set = {'no', 'false', 'f', 'n'}
    if value.lower() in true_set:
      return True
    if value.lower() in false_set:
      return False
    return None

  def GetType(self, value: str) -> Any:
    """Infer the type of a string's representation.

    Default to str if the underlying string is neither of: [bool, int, float].

    Args:
      value (str): The string to infer the type from.

    Returns:
      Any: The type for the string.
    """
    if self.Str2Bool(value) in [False, True]:
      return bool

    if self.IsInt(value):
      return int

    if self.IsFloat(value):
      return float

    return str

  def CastToType(self, value: str, value_type: Any) -> Any:
    """Cast a string to the desired type.

    Returns None if the string cannot be cast to the desired type.

    Args:
      value (str): The string to cast.
      value_type (Any): The type to cast the string to.
    """
    if value_type == int:
      if not self.IsInt(value):
        return None
      return int(float(value))

    if value_type == float:
      if not self.IsFloat(value):
        return None
      return float(value)

    if value_type == bool:
      if self.Str2Bool(value) is None:
        return None
      return self.Str2Bool(value)

    return value

  @staticmethod
  def Marshal(st: session.SessionSettable) -> Dict[str, Any]:
    """Marshal a SessionSettable object to a JSON dictionary.

    Args:
      st (SessionSettable): The settable to marshal.

    Returns:
      Dict[str, Any]: A JSON dictionary representation of the settable.
    """
    return {
        'session_id': st.session_id,
        'recipe': st.recipe,
        'name': st.name,
        'description': st.description,
        'value': st.GetValue(),
        'type': st.type.__name__,
        'optional': st.IsOptional()
    }

  @staticmethod
  def Unmarshal(st: Dict[str, Any]) -> session.SessionSettable:
    """Unmarshal a JSON dictionary to a SessionSettable object.

    Args:
      st (Dict[str, Any]): The JSON dictionary representation of the settable.

    Returns:
      SessionSettable: A SessionSettable object.
    """
    s = session.SessionSettable(
        st['session_id'],
        st['recipe'],
        st['name'],
        st['description'],
        locate(st['type']),
        optional=st['optional']
    )
    s.SetValue(st['value'])
    return s

  def ReadSessionFromFile(self, unmarshal: bool = True) -> Dict[str, Any]:
    """Read Metawolf's sessions from file.

    Args:
      unmarshal (bool): Boolean that indicates whether or not the returned
          dictionary should contain unmarshalled objects.

    Returns:
      Dict[str, Dict[str, Dict[str, Union[str, SessionSettable]]]]: A
          dictionary that maps session IDs and recipes to their corresponding
          settable (or JSON str).
    """
    # pylint: disable=line-too-long
    loaded_sessions = {}  # type: Dict[str, Dict[str, Dict[str, Union[str, session.SessionSettable]]]]
    # pylint: enable=line-too-long
    if not os.path.exists(os.path.expanduser(self.session_path)):
      return loaded_sessions

    with open(os.path.expanduser(self.session_path), 'r') as f:
      if f.read(1):
        f.seek(0)
        sessions = json.loads(f.read())
      else:
        return loaded_sessions

    for session_id, value in sessions.items():
      if session_id == LAST_ACTIVE_SESSION:
        # In this case, value holds the value of the latest used session and is
        # not a dictionary
        loaded_sessions[session_id] = value
        continue
      loaded_sessions[session_id] = {}
      for recipe, settables in value.items():
        if recipe == LAST_ACTIVE_RECIPE:
          # In this case, settables holds the value of the latest used recipe
          # and is not a dictionary
          loaded_sessions[session_id][LAST_ACTIVE_RECIPE] = settables
          continue
        if recipe == LAST_ACTIVE_PROCESSES:
          # In this case, settables holds the list of processes run in the
          # session
          loaded_sessions[session_id][LAST_ACTIVE_PROCESSES] = settables
          continue
        loaded_sessions[session_id][recipe] = {}
        for settable_id, settable in settables.items():
          loaded_sessions[session_id][recipe][settable_id] = self.Unmarshal(
              settable) if unmarshal else settable

    return loaded_sessions

  def RunInBackground(
      self,
      processes: List['output.MetawolfProcess']
  ) -> bool:
    """Guard executed before `quit` or SIGINT.

    If processes are still running, ask the user if they want to let them run
    in the background.

    Args:
      processes (List[output.MetawolfProcess]): The processes associated to
          Metawolf's session.

    Returns:
      bool: True if the processes should keep running in the background.
    """
    still_running = False
    for metawolf_process in processes:
      if metawolf_process.Poll() is None:
        still_running = True
        break
    if still_running:
      value = input('Metawolf still has running processes. Would you like to '
                    'keep them running in the background [Yn]? ') or 'y'
      q = self.Str2Bool(str(value))
      while q not in [False, True]:
        value = input('[Yn]? ') or 'y'
        q = self.Str2Bool(str(value))
      return q
    return True

  def PrepareDFTimewolfCommand(
      self,
      recipe: str,
      session_settables: Dict[str, session.SessionSettable]
  ) -> List[str]:
    """Builds a cli command from current session parameters.

    Args:
      recipe (str): The name of the recipe to run.
      session_settables (Dict[str, SessionSettable]): The dictionary holding the
          session settables to use to build the command.

    Returns:
      List[str]: A list that contains the CLI command elements based on the
          current recipe and settables.
    """
    cmd_components = {}
    for _, settable in session_settables.items():
      if settable.name == SESSION_ID_SETTABLE:
        continue
      if not settable.IsOptional():
        value = settable.GetValue()
        if value is None:
          return []
        cmd_components[settable.name] = '{0!s}'.format(value)
      else:
        value = settable.GetValue()
        if value:
          cmd_components[settable.name] = '--{0:s}={1!s}'.format(
              settable.name, value)

    # We need to order the arguments as they are defined in the recipe
    cmd = [DFTIMEWOLF, recipe]
    for name, _, _ in self.recipe_manager.Recipes()[recipe].args:
      if name.startswith('--'):
        name = name.replace('--', '')
      if name in cmd_components:
        cmd.append(cmd_components[name])
    return cmd

  def GetRecipes(self) -> Dict[str, str]:
    """Return available DFTimewolf recipes.

    Returns:
      Dict[str, str]: A dictionary that maps recipe names to their short
          description.
    """
    recipes = {}
    for recipe in self.recipe_manager.GetRecipes():
      short_desc = ' '.join(recipe.GetHelpString().split())
      short_desc = short_desc.replace(recipe.name, '').strip()
      recipes[recipe.name] = short_desc
    return recipes

  def GetRecipe(self, recipe_name: str) -> Optional[resources.Recipe]:
    """Return a DFTimewolf Recipe object.

    Args:
      recipe_name (str): The name of the recipe to return.

    Returns:
      Recipe: The recipe object if recipe_name was found, or None.
    """
    return self.Recipes().get(recipe_name)

  def Recipes(self) -> Dict[str, resources.Recipe]:
    """Return a dictionary that maps recipe names to Recipe objects."""
    return self.recipe_manager.Recipes()
