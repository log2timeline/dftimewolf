#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import subprocess
import tempfile
import uuid
from pydoc import locate
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from typing.io import IO

from dftimewolf.lib import errors

from dftimewolf.cli import dftimewolf_recipes
from dftimewolf.metawolf import output
from dftimewolf.metawolf import session

METAWOLF_PATH = '~/.metawolf'
DFTIMEWOLF = 'dftimewolf'

LAST_ACTIVE_SESSION = 'last_active_session'
LAST_ACTIVE_RECIPE = 'last_active_recipe'
SESSION_ID_SETTABLE = 'session_id'

CRITICAL_ERROR = 'Critical error found. Aborting.'


class MetawolfUtils:
  """MetawolfUtils holds a set of utility methods for Metawolf.

  Attributes:
    recipe_manager (RecipeManager): A DFTimewolf RecipeManager object.
  """

  def __init__(self):
    self.recipe_manager = self.GetDFTool().RecipeManager()

  @staticmethod
  def GetDFTool() -> dftimewolf_recipes.DFTimewolfTool:
    """Get a DFTimewolfTool object."""
    tool = dftimewolf_recipes.DFTimewolfTool()
    tool.LoadConfiguration()
    try:
      tool.ReadRecipes()
    except (KeyError,
            errors.RecipeParseError,
            errors.CriticalError) as exception:
      print(exception)
      exit(1)
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
      float_n = float(value)
      _ = int(float_n)
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
  def str2bool(value: str) -> Optional[bool]:
    """Convert a string to its boolean representation.

    Args:
      value (str): The value to convert to a boolean.

    Returns:
      Optional[bool]: True/False if the string can be associated to a boolean,
          None otherwise.
    """
    if not isinstance(value, str):
      return None
    true_set = {'yes', 'true', 't', 'y', '1'}
    false_set = {'no', 'false', 'f', 'n', '0'}
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
    if self.str2bool(value) in [False, True]:
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
      if self.str2bool(value) is None:
        return None
      return self.str2bool(value)

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
    loaded_sessions = {}
    if not os.path.exists(os.path.expanduser(METAWOLF_PATH)):
      return loaded_sessions

    with open(os.path.expanduser(METAWOLF_PATH), 'r') as f:
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
        loaded_sessions[session_id][recipe] = {}
        for settable_id, settable in settables.items():
          loaded_sessions[session_id][recipe][settable_id] = self.Unmarshal(
              settable) if unmarshal else settable

    return loaded_sessions

  @staticmethod
  def RunRecipe(cmd: List[str]) -> Tuple[subprocess.Popen, IO]:
    """Run a DFTimewolf recipe in a separate process.

    Args:
      cmd (List[str]): The recipe and its arguments.

    Returns:
      Tuple[subprocess.Popes, IO]: The process running the recipe and the file
          the output is written to.
    """

    # Temporary files are closed either:
    #  - when detecting a `quit` or SIGINT
    #  - through garbage collection in any other scenario
    out = tempfile.TemporaryFile(mode='w+')
    process = subprocess.Popen(
        cmd, shell=False, stdout=out, stderr=out, text=True)
    return process, out

  def TerminateRunningProcesses(
      self,
      processes: Dict[Tuple[str, str], Tuple[subprocess.Popen, IO, int]]
  ) -> bool:
    """Guard executed before `quit` or SIGINT.

    If processes are still running, ask the user if they are sure they want
    to quit Metawolf. If so, kill any running process to exit gracefully.

    Args:
      processes (Dict[Tuple[str, str], Tuple[Popen, IO, int]): The processes
          dictionary which holds the processes running Metawolf's commands.

    Returns:
      bool: True if it is safe to quit.
    """
    still_running = False
    for _, proc_info in processes.items():
      process, _, _ = proc_info
      if process.poll() is None:
        still_running = True
    if still_running:
      value = input('Metawolf is still running commands. Are you sure you want '
                    'to quit (y/n)? ')
      q = self.str2bool(str(value))
      while q not in [False, True]:
        value = input('y/n? ')
        q = self.str2bool(str(value))
      return q
    return True

  @staticmethod
  def GetProcessStatus(out: IO, process: subprocess.Popen) -> str:
    """Return a process status.

    Args:
      out (IO): The IO object containing the process' stdout/stderr.
      process (Popen): The process object.

    Returns:
      str: The status of the running recipe.
    """
    # https://docs.python.org/3/library/subprocess.html#subprocess.Popen.returncode
    err = process.poll()

    if err is None:
      return output.MetawolfOutput.Color('Running', output.YELLOW)

    # Process can be in 3 states: interrupted, failed, or completed.
    if err < 0:
      return output.MetawolfOutput.Color('Interrupted', output.RED)
    out.seek(0)
    if CRITICAL_ERROR in out.read():
      return output.MetawolfOutput.Color('Failed', output.RED)
    return output.MetawolfOutput.Color('Completed', output.GREEN)

  @staticmethod
  def CleanupProcesses(
      processes: Dict[Tuple[str, str], Tuple[subprocess.Popen, IO, int]]
  ) -> None:
    """Close open IO objects linked to subprocesses stdout and stderr.

    Terminate running processes.

    Args:
      processes (Dict[Tuple[str, str], Tuple[Popen, IO, int]): The processes
          dictionary which holds the files to close.
    """
    for _, proc_info in processes.items():
      process, out, _ = proc_info
      if process.poll() is None:
        # process is still running, kill it
        process.terminate()
      # Close the IO object.
      out.close()

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
        else:
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
      Dict[str, str]: A dictionary that maps recipe names to their description.
    """
    recipes = {}
    for recipe in self.recipe_manager.GetRecipes():
      recipes[recipe.name] = recipe.description
    return recipes

  def Recipes(self):
    """Return a dictionary that maps recipe names to Recipe objects."""
    return self.recipe_manager.Recipes()
