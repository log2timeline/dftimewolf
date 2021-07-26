#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Metawolf main entrypoint."""

import argparse
import json
import os
import sys
import signal

from types import FrameType
from typing import Dict, Optional, Union, Any, List

import cmd2  # pylint: disable=import-error
from prettytable import PrettyTable  # pylint: disable=import-error

from dftimewolf.metawolf import session
from dftimewolf.metawolf import utils
from dftimewolf.metawolf import output

SESSION_ID_NOT_INITIALIZE = 'TODO'
SESSION_ID_SETTABLE = 'session'
RECIPE_SETTABLE = 'recipe'
RECIPE_NAME_IGNORED = 'IGNORED'

SHOW_RECIPES = 'recipes'
SHOW_RECIPE = 'recipe'
SHOW_SESSIONS = 'sessions'
SHOW_RUNNING = 'running'
SHOW_OUTPUT = 'output'
SET_ALL = 'all'

LAST_ACTIVE_SESSION = 'last_active_session'
LAST_ACTIVE_RECIPE = 'last_active_recipe'
LAST_ACTIVE_PROCESSES = 'last_active_processes'


class Metawolf(cmd2.Cmd):
  """Metawolf is a Meterpreter-like shell for DFTimewolf.

  Attributes:
    metawolf_output (MetawolfOutput): Metawolf's output utilities.
    metawolf_utils (MetawolfUtils): Metawolf utilities.
    session_settables (Dict[str, SessionSettable]):
        Dictionary which holds the settables, keyed by a string of the form
        session_ID-recipe_name-settable_name.
    processes (List[output.MetawolfProcess]): Holds the current metawolf
        processes.
    last_active_session (str): Holds the value of the last active session.
    reload_settables (bool): If True, reload the recipe's settables.
    copy_over (bool): If True, settables values will be copied over to the new
        recipe if the recipe shares similar (i.e. same name) arguments.
    nb_running_processes (int): Number of processes run in the session.
    debug (bool): Boolean indicating whether or not to show stack traces during
        exceptions.
    recipe_settable (SessionSettable): The settable object for the recipe.
    session_id_settable (SessionSettable): The settable object for the session.
    sessions (Dict[str, Dict[str, Dict[str, SessionSettable]]]): Dictionary
        which maps a session and recipe to the corresponding dictionary of
        settables.
    recipes (Dict[str, str]): Dictionary which maps recipe names to their
        description.
  """
  # Method names must follow the format do_xxx to be exposed to cmd2.
  # pylint: disable=invalid-name
  def __init__(self) -> None:
    super(Metawolf, self).__init__(shortcuts=cmd2.DEFAULT_SHORTCUTS)

    self.metawolf_output = output.MetawolfOutput()
    self.metawolf_utils = utils.MetawolfUtils()

    self._settables = {}  # Ignore default CMD2 settables
    self.session_settables = {}  # type: Dict[str, session.SessionSettable]
    self.processes = []  # type: List[output.MetawolfProcess]

    self.last_active_session = None  # type: Optional[str]
    self.reload_settables = False
    self.reload_default = False
    self.copy_over = False
    self.nb_running_processes = 0
    self.debug = True

    self.recipe_settable = session.SessionSettable(
        SESSION_ID_NOT_INITIALIZE,
        RECIPE_NAME_IGNORED,
        RECIPE_SETTABLE,
        'Recipe to use. Type `{0:s}` to see available recipes.'.format(
            self.metawolf_output.Color('show recipes', output.YELLOW)),
        str)
    self.AddSessionSettable(self.recipe_settable)

    self.session_id_settable = session.SessionSettable(
        SESSION_ID_NOT_INITIALIZE,
        RECIPE_NAME_IGNORED,
        SESSION_ID_SETTABLE,
        'Metawolf\'s session_id. Type `{0:s}` to display existing '
        'sessions, and switch with `{1:s}`. A session has '
        'the form incident_id-recipe'.format(
            self.metawolf_output.Color('show sessions', output.YELLOW),
            self.metawolf_output.Color('set session session', output.YELLOW)),
        str)
    self.AddSessionSettable(self.session_id_settable)

    self.sessions = self.LoadSession()
    self.recipes = self.metawolf_utils.GetRecipes()
    self.metawolf_output.Welcome()

  @property
  def recipe(self) -> Any:
    """Return recipe settable's value."""
    return self.recipe_settable.GetValue()

  @property
  def session_id(self) -> Any:
    """Return session settable's value."""
    return self.session_id_settable.GetValue()

  def postcmd(self, stop: bool, statement: Union[cmd2.Statement, str]) -> bool:
    """This is called right after any shell input.

    We override this to save Metawolf's session between each call, and write it
    to file. If the recipe is changed the settables are reloaded to match
    the new recipe's arguments.

    Args:
      stop (bool): True to terminate the cmd loop.
      statement (Statement): The user's input.

    Returns:
      bool: Whether or not to terminate the cmd loop.
    """
    if self.session_id:
      self.SaveSession()
      self.SetSessionID(self.session_id)
      if self.reload_settables:
        self.ReloadSettables()
      if self.session_id not in self.sessions:
        self.sessions[self.session_id] = {}
      if self.recipe:
        self.sessions[self.session_id][LAST_ACTIVE_RECIPE] = self.recipe
        self.sessions[self.session_id][self.recipe] = self.session_settables

    return super(Metawolf, self).postcmd(stop, statement)

  def do_new(self, _: cmd2.Statement) -> None:
    """Create a new session.

    Args:
      _ (Statement): Unused.
    """
    session_id = self.metawolf_utils.CreateNewSessionID()
    self.recipe_settable.SetValue(None)
    self.reload_settables = False
    self.copy_over = False
    self.ClearSessionSettables()
    self.SetSessionID(session_id)
    self.sessions[session_id] = {}

  def do_set(self, args: argparse.Namespace) -> None:
    """Set arguments for Metawolf.

    Args:
      args (argparse.Namespace): The arguments from the user's input.
    """

    if not args.args:
      t = PrettyTable(['Name', 'Description', 'Type', 'Current Value'],
                      align='l')
      for _, settable in self.session_settables.items():
        value = settable.GetValue()
        t.add_row(
            [self.metawolf_output.Color(settable.name, output.GREEN),
             settable.description,
             settable.type.__name__,
             self.metawolf_output.Color(
                 value, output.GREEN) if value is not None else value
             ])
      print(t)
      return

    what = args.args.split(' ')
    if len(what) != 2 and what[0] != SET_ALL:
      print('Usage: `{0:s}` to set a parameter\'s value || `{1:s}` to '
            'interactively set all current recipe\'s parameters.'.format(
          self.metawolf_output.Color('set arg_name arg_value', output.YELLOW),
          self.metawolf_output.Color('set all', output.YELLOW)))
      return

    if what[0] == SET_ALL:
      if self.session_id and self.recipe:
        for _, settable in self.session_settables.items():
          if settable.recipe == RECIPE_NAME_IGNORED:
            # Session and recipe settables are not in scope.
            continue
          value = input('Value for parameter {0:s} ({1:s}: {2:s}. Press '
                        '"enter" to skip.): '.format(
              settable.name,
              self.metawolf_output.Color('Current value', output.YELLOW),
              self.metawolf_output.Color(settable.GetValue(), output.GREEN)))
          value = str(value).strip()
          if not value:
            continue
          updated = self.UpdateSessionSettable(value, settable=settable)
          while not updated:
            value = input('Value for parameter {0:s}: '.format(settable.name))
            value = str(value).strip()
            updated = self.UpdateSessionSettable(value, settable=settable)
      return

    if what[0] == SESSION_ID_SETTABLE:
      session_id = what[1]
      if session_id not in self.sessions:
        print(self.metawolf_output.Color('Session {0:s} does not exist.'.format(
            session_id), output.RED))
        return

      self.SetSessionID(session_id)
      last_active = self.sessions.get(session_id, {}).get(LAST_ACTIVE_RECIPE)
      if last_active:
        self.recipe_settable.SetValue(last_active)
      else:
        self.recipe_settable.SetValue(None)
        self.ClearSessionSettables()
      self.reload_settables = True
      return

    if what[0] == RECIPE_SETTABLE:
      recipe = what[1]
      if recipe not in self.recipes:
        print(self.metawolf_output.Color(
            'Recipe {0:s} does not exist.'.format(recipe), output.RED))
        return

      if self.recipe:
        # If a recipe is already set, prompt the user for copy over option
        value = input('Would you like to copy over previous recipe ({0:s}) '
                      'arguments to the new recipe ({1:s}): [yN]? '.format(
            self.recipe, recipe)) or 'n'
        copy_over = self.metawolf_utils.Str2Bool(str(value))
        while copy_over not in [False, True]:
          value = input('[yN]? ') or 'n'
          copy_over = self.metawolf_utils.Str2Bool(str(value))
        self.copy_over = copy_over

      if self.recipe != recipe:
        # Recipe changed, we need to reload the settables.
        self.reload_settables = True

      self.recipe_settable.SetValue(recipe)
    else:
      # This block happens whenever a recipe's argument / unknown argument
      # is set
      s_id = None
      if self.session_id:
        if self.recipe:
          s_id = '{0:s}-{1:s}-{2:s}'.format(
              self.session_id, self.recipe, what[0])
        else:
          if what[0] != SESSION_ID_SETTABLE:
            print('You must set a recipe first: `{0:s}`'.format(
                self.metawolf_output.Color('set recipe name', output.YELLOW)))
          return
      if s_id in self.session_settables:
        _ = self.UpdateSessionSettable(what[1], s_id=s_id)
      else:
        print(self.metawolf_output.Color(
            '{0:s} is not a settable attribute.'.format(what[0]), output.RED))

  def do_run(self, _: cmd2.Statement) -> None:
    """Run a DFTimewolf recipe. Show running recipes: `show running`.

    This will run whatever recipe is currently being used in the session.

    Args:
      _ (Statement): Unused.
    """
    if not self.session_id or not self.recipe:
      print(self.metawolf_output.Color(
          'No session/recipe detected, nothing to run.', output.RED))
      return

    cmd = self.metawolf_utils.PrepareDFTimewolfCommand(
        self.recipe, self.session_settables)
    if not cmd:
      print('Some parameters are missing. Type `{0:s}` to see which parameter'
            ' you need to set and their current values.'.format(
          self.metawolf_output.Color('set', output.YELLOW)))
      return

    value = input('Confirm running: {0:s} [yN]? '.format(
        self.metawolf_output.Color(' '.join(cmd), output.YELLOW))) or 'n'
    ans = self.metawolf_utils.Str2Bool(str(value))
    while ans not in [False, True]:
      value = input('[yN]? ') or 'n'
      ans = self.metawolf_utils.Str2Bool(str(value))
    if not ans:
      return

    print('Running: {0:s}'.format(
        self.metawolf_output.Color(' '.join(cmd), output.YELLOW)))

    metawolf_process = output.MetawolfProcess(
        session_id=self.session_id,
        cmd=cmd,
        output_id=self.nb_running_processes)
    metawolf_process.Run()

    self.processes.append(metawolf_process)
    self.nb_running_processes += 1

  def do_show(self, st: cmd2.Statement) -> None:
    """Show various information about the current session.

    Possible choices: [`recipes`, `recipe recipe_name`, `sessions`, `running`,
    `output output_id`]. `recipes` shows the user the available DFTimewolf
    recipes, while `recipe recipe_name` shows the details of a given recipe.
    `sessions` shows the currently available Metawolf's sessions and any recipe
    in use, along with information about the recipe's state. `running`
    displays running jobs and their state. `output output_id` prints to
    STDOUT the output of the matching output_id.

    Args:
      st (Statement): The user's input.
    """
    if not st.args:
      print('Usage of show: `{0:s}`'.format(
          self.metawolf_output.Color(
              'show [recipes, recipe recipe_name, sessions, running, '
              'output output_id]', output.YELLOW)))
      return

    if st.args == SHOW_RECIPES:
      t = PrettyTable(['Name', 'Description'], align='l')
      for recipe_name, recipe_desc in self.recipes.items():
        t.add_row([
            self.metawolf_output.Color(recipe_name, output.GREEN),
            recipe_desc])
      print(t)
      return

    if st.args == SHOW_SESSIONS and self.sessions:
      t = PrettyTable(
          ['Session ID (`{0:s}` or `{1:s}`)'.format(
              self.metawolf_output.Color('new', output.YELLOW),
              self.metawolf_output.Color('set session session', output.YELLOW)),
           'Recipes in use',
           'Status (latest run)',
           'Timestamp (UTC)'],
          align='l')
      for s_id, s in self.sessions.items():
        if s_id == LAST_ACTIVE_SESSION:
          continue
        active_recipes = []
        for recipe, _ in s.items():
          if recipe in [LAST_ACTIVE_RECIPE, LAST_ACTIVE_PROCESSES]:
            continue
          active_recipes.append(recipe)
        statuses = {}
        for metawolf_process in self.processes:
          if s_id == metawolf_process.session_id and metawolf_process.recipe:
            statuses[metawolf_process.recipe] = (
                metawolf_process.Status(),
                metawolf_process.timestamp_readable or ''
            )  # latest status of recipe run
        t.add_row(
            [self.metawolf_output.Color(s_id, output.GREEN),
             '\n'.join(active_recipes),
             '\n'.join([s for s, _ in statuses.values()]),
             '\n'.join([t for _, t in statuses.values()])])
      print(t)
      return

    if st.args == SHOW_RUNNING:
      table = PrettyTable(
        ['Session ID',
         'Command ID (`{0:s}`)'.format(
             self.metawolf_output.Color('kill command_id', output.YELLOW)),
         'Timestamp (UTC)',
         'Command',
         'Status',
         'Output ID (`{0:s}`)'.format(
             self.metawolf_output.Color(
                 'show output_id output_id', output.YELLOW))],
        align='l')
      for metawolf_process in self.processes:
        table.add_row(
            [metawolf_process.session_id,
             metawolf_process.cmd_id,
             metawolf_process.timestamp_readable,
             metawolf_process.cmd_readable,
             metawolf_process.Status(),
             metawolf_process.output_id])
      print(table)
      return

    # Otherwise, check if we show an output or a recipe details
    user_input = st.args.split(' ')
    if len(user_input) != 2:
      # Malformed command, do nothing.
      print('Malformed command. Type `{0:s}` to see available options.'.format(
          self.metawolf_output.Color('show', output.YELLOW)))
      return

    action, value = user_input

    if action == SHOW_RECIPE:
      df_recipe = self.metawolf_utils.GetRecipe(value)
      if not df_recipe:
        print(self.metawolf_output.Color(
            'Recipe {0!s} does not exist.'.format(value), output.RED))
        return

      # Recipe description
      t = PrettyTable(
          [self.metawolf_output.Color(df_recipe.name, output.GREEN)], align='l')
      t.add_row([df_recipe.description])
      print(t)

      # Recipe's arguments
      t = PrettyTable(
          ['Argument', 'Description'],
          align='l')
      for name, desc, _ in df_recipe.args:
        is_optional = name.startswith('--')
        if is_optional:
          name = name.replace('--', '')
          desc = self.metawolf_output.Color(
              '[Optional]. ', output.YELLOW) + desc
        t.add_row([self.metawolf_output.Color(name, output.GREEN), desc])
      print(t)
      return

    if action == SHOW_OUTPUT:
      for metawolf_process in self.processes:
        if value == str(metawolf_process.output_id):
          out = metawolf_process.Read()
          if out:
            print(out)

  def do_reload(self, _: cmd2.Statement) -> None:
    """Reload the default recipe arguments.

    Args:
      _ (Statement): Unused.
    """
    self.reload_settables = True
    self.reload_default = True

  def do_clear(self, _: cmd2.Statement) -> None:
    """Clear the recipe's settable values.

    Args:
      _ (Statement): Unused.
    """
    # mypy associates the unused argument to below for-loop, so we ignore it.
    for _, settable in self.session_settables.items():  # type: ignore
      if settable.name in [SESSION_ID_SETTABLE, RECIPE_SETTABLE]:
        continue
      settable.SetValue(None)

  def do_clean(self, _: cmd2.Statement) -> None:
    """Clean the processes associated to the current session.

    - Delete output files
    - Remove metawolf's runs from session file
    - Reset output counter

    Args:
      _ (Statement): Unused.
    """
    for metawolf_process in self.processes:
      if metawolf_process.Poll() is None:
        metawolf_process.Terminate()
      if metawolf_process.outfile_path:
        try:
          os.remove(metawolf_process.outfile_path)
        except FileNotFoundError:
          pass
    self.nb_running_processes = 0
    self.processes = []

  def do_kill(self, st: cmd2.Statement) -> None:
    """Kill a running recipe.

    Args:
      st (Statement): The user's input.
    """
    if not st.args:
      print(self.metawolf_output.Color(
          'Usage of kill: `kill command_id`.', output.YELLOW))
      return

    for metawolf_process in self.processes:
      if metawolf_process.cmd_id == st.args:
        metawolf_process.Terminate()
        break

  def do_quit(self, _: argparse.Namespace) -> Optional[bool]:
    """Quit Metawolf.

    Args:
      _ (argparse.Namespace): Unused.

    Returns:
      Optional[bool]: True if the shell should be stopped.
    """
    if not self.metawolf_utils.RunInBackground(self.processes):
      # Close any open files / terminate running processes
      for metawolf_process in self.processes:
        metawolf_process.Terminate()
    return super(Metawolf, self).do_quit(_)  # type: ignore

  def sigint_handler(self, signum: int, _: FrameType) -> None:
    """Handle SIGINT.

    Args:
      signum (int): Signal number.
      _ (FrameType): Unused.
    """

    if signum == signal.SIGINT:
      if not self.metawolf_utils.RunInBackground(self.processes):
        # Close any open files / terminate running processes
        for metawolf_process in self.processes:
          metawolf_process.Terminate()
      self.SaveSession()
      sys.exit(signum)
    else:
      super(Metawolf, self).sigint_handler(signum, _)

  def LoadSession(
      self) -> Dict[str, Dict[str, Dict[str, session.SessionSettable]]]:
    """Load all existing Metawolf sessions.

    Returns:
      Dict[str, Dict[str, Dict[str, SessionSettable]]]: A dictionary that maps
          each session to all loaded recipes, themselves matching their
          settables.
    """

    loaded_sessions = self.metawolf_utils.ReadSessionFromFile()

    last_session = loaded_sessions.get(LAST_ACTIVE_SESSION)
    if last_session:
      session_id = last_session
    else:
      # No sessions found, create a new one
      session_id = self.metawolf_utils.CreateNewSessionID()
      loaded_sessions[session_id] = {}

    last_recipe = loaded_sessions[session_id].get(LAST_ACTIVE_RECIPE)
    if last_recipe and last_recipe != self.recipe:
      self.recipe_settable.SetValue(last_recipe)

    self.SetSessionID(session_id)

    for recipe, settables in loaded_sessions.get(self.session_id, {}).items():
      if recipe == LAST_ACTIVE_RECIPE or not last_recipe:
        continue
      if recipe == LAST_ACTIVE_PROCESSES:
        # Restore self.processes
        for _, metawolf_process in settables.items():
          proc = output.MetawolfProcess(from_dict=metawolf_process)
          self.processes.append(proc)
        continue
      for settable_id, settable in settables.items():
        s_id = '{0:s}-{1:s}-{2:s}'.format(
            self.session_id, self.recipe, settable.name)
        if settable_id == s_id and settable_id not in self.session_settables:
          self.AddSessionSettable(settable)

    # Reset current nb of proc
    if self.processes:
      self.nb_running_processes = max(
          [proc.output_id for proc in self.processes]) + 1
    return loaded_sessions

  def SaveSession(self) -> None:
    """Save Metawolf's session."""

    if not self.session_id:
      return

    # Load session file, and update it with current session info.
    current_sessions = self.metawolf_utils.ReadSessionFromFile(unmarshal=False)
    current_sessions[LAST_ACTIVE_SESSION] = self.session_id

    if self.session_id not in current_sessions:
      current_sessions[self.session_id] = {}

    if self.recipe:
      current_sessions[self.session_id][LAST_ACTIVE_RECIPE] = self.recipe
      if self.recipe not in current_sessions[self.session_id]:
        current_sessions[self.session_id][self.recipe] = {}
      for settable_id, settable in self.session_settables.items():
        # Skip recipe's settable
        if settable_id.startswith(SESSION_ID_NOT_INITIALIZE):
          continue
        s_id = '{0:s}-{1:s}-{2:s}'.format(
            self.session_id, self.recipe, settable.name)
        if settable_id == s_id:
          # pylint: disable=line-too-long
          current_sessions[self.session_id][self.recipe][settable_id] = self.metawolf_utils.Marshal(settable)
          # pylint: enable=line-too-long

    # If we cleared processes
    if not self.processes:
      current_sessions[self.session_id][LAST_ACTIVE_PROCESSES] = {}

    # Save process state
    for metawolf_process in self.processes:
      if LAST_ACTIVE_PROCESSES not in current_sessions[self.session_id]:
        current_sessions[self.session_id][LAST_ACTIVE_PROCESSES] = {}
      current_sessions[self.session_id][LAST_ACTIVE_PROCESSES][
        metawolf_process.cmd_id] = metawolf_process.Marshal()

    with open(os.path.expanduser(utils.METAWOLF_PATH), 'w') as f:
      f.write(json.dumps(current_sessions))

  def SetSessionID(self, session_id: str) -> None:
    """Update Metawolf's session ID.

    This also updates the prompt shown to the user.

    Args:
      session_id (str): The session ID.
    """

    self.session_id_settable.SetValue(session_id)
    self.last_active_session = session_id
    prompt = ''
    if self.session_id:
      prompt += self.metawolf_output.Color('${0:s}'.format(
          self.session_id), output.PURPLE)
    if self.recipe:
      prompt += self.metawolf_output.Color('${0:s}'.format(
          self.recipe), output.BLUE)
    prompt += self.metawolf_output.Color('> ', output.BLUE)
    # self.prompt is inherited from cmd2
    self.prompt = prompt  # pylint: disable=attribute-defined-outside-init

  def ReloadSettables(self) -> None:
    """Reload Metawolf's settables based on the current recipe."""

    if not self.session_id or not self.recipe:
      return

    # We need to check whether or not we're switching to an existing session.
    # If so, we need to set the settables back to their values.
    current_sessions = self.metawolf_utils.ReadSessionFromFile()
    if self.copy_over:
      previous_settables = {
          settable.name: settable.GetValue(
              ) for settable in self.session_settables.values()
      }

    self.ClearSessionSettables()

    # Add current recipe's settables
    recipes = self.metawolf_utils.Recipes()
    for name, desc, default_value in recipes[self.recipe].args:
      t = type(default_value) if default_value is not None else str
      is_optional = name.startswith('--')
      if is_optional:
        name = name.replace('--', '')
        desc = self.metawolf_output.Color('[Optional]. ', output.YELLOW) + desc
      s_id = '{0:s}-{1:s}-{2:s}'.format(self.session_id, self.recipe, name)
      if s_id not in self.session_settables or self.reload_default:
        current_settable = current_sessions.get(self.session_id, {}).get(
            self.recipe, {}).get(s_id)
        if current_settable and not self.reload_default:
          session_settable = current_settable
        else:
          session_settable = session.SessionSettable(
              self.session_id, self.recipe, name, desc, t, optional=is_optional)
          # Populate default value from recipe
          session_settable.SetValue(default_value)

        if self.copy_over:
          # Copy over option takes precedence over previous settable values
          # stored on file for matching settables.
          if name in previous_settables:
            session_settable.SetValue(previous_settables[session_settable.name])

        self.AddSessionSettable(session_settable)

    # Recipes just reloaded, so we can turn this off.
    self.reload_settables = False
    self.copy_over = False

  def AddSessionSettable(self, settable: session.SessionSettable) -> None:
    """Add a new session settable to the session's dictionary.

    Args:
      settable (SessionSettable): The settable to add.
    """
    s_id = '{0:s}-{1:s}-{2:s}'.format(
        settable.session_id, settable.recipe, settable.name)
    self.session_settables[s_id] = settable

  def RemoveSessionSettable(self, settable: session.SessionSettable) -> None:
    """Delete a session settable from the session's dictionary.

    Args:
      settable (SessionSettable): The settable to delete.
    """
    try:
      s_id = '{0:s}-{1:s}-{2:s}'.format(
          settable.session_id, settable.recipe, settable.name)
      del self.session_settables[s_id]
    except KeyError:
      pass

  def UpdateSessionSettable(
      self,
      updated_value: Any,
      s_id: Optional[str] = None,
      settable: Optional[session.SessionSettable] = None
  ) -> bool:
    """Update a settable's value.

    Args:
      updated_value (Any): The value to update the settable with.
      s_id (str): Optional. The settable ID. If not provided, settable must be.
      settable (SessionSettable): The settable to update. If not provided,
          settable must be.

    Returns:
      bool: True if the settable was correctly updated, False otherwise.
    """
    if not s_id and not settable:
      return False

    settable = self.session_settables.get(s_id) if s_id else settable
    if not settable:
      return False

    prev_value = settable.GetValue()
    value = self.metawolf_utils.CastToType(updated_value, settable.type)
    if not value:
      input_type = self.metawolf_utils.GetType(updated_value)
      print(self.metawolf_output.Color(
          'Cannot use: {0:s} (of type {1!s}) for recipe argument: {2:s} '
          '(of type {3!s})'.format(
              updated_value, input_type, settable.name, settable.type),
          output.RED))
      return False

    settable.SetValue(value)
    out = self.metawolf_output.Color(
        '{0:s}: '.format(settable.name), output.YELLOW)
    out += self.metawolf_output.Color(prev_value, output.RED)
    out += ' --> '
    out += self.metawolf_output.Color(value, output.GREEN)
    print(out)
    return True

  def ClearSessionSettables(self) -> None:
    """Clear current settables."""
    to_remove = []
    for _, settable in self.session_settables.items():
      if settable.name not in [RECIPE_SETTABLE, SESSION_ID_SETTABLE]:
        to_remove.append(settable)
    for settable in to_remove:
      self.RemoveSessionSettable(settable)


if __name__ == "__main__":
  sys.exit(Metawolf().cmdloop())
