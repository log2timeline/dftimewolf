#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Metawolf main entrypoint."""

import argparse
import json
import os
import shlex
import sys
import signal

from types import FrameType
from typing import Dict, Optional, Union, Any, List

import cmd2  # pylint: disable=import-error
import cmd2.ansi as cmd2_ansi  # pylint: disable=import-error
from prettytable import PrettyTable  # pylint: disable=import-error

from dftimewolf.metawolf import session
from dftimewolf.metawolf import utils
from dftimewolf.metawolf import output

SESSION_ID_NOT_INITIALIZE = 'TODO'
RECIPE_NAME_IGNORED = 'IGNORED'

ARG_RECIPES = '-recipes'
ARG_RECIPE = '-recipe'
ARG_SESSIONS = '-sessions'
ARG_SESSION = '-session'
ARG_RUNNING = '-running'
ARG_OUTPUT = '-output'
ARG_INPUT = '-input'
ARG_PARAMETER = '-parameter'
ARG_RECIPES_SC = '-rs'
ARG_RECIPE_SC = '-r'
ARG_SESSIONS_SC = '-s'
ARG_RUNNING_SC = '-rn'
ARG_OUTPUT_SC = '-o'
ARG_PARAMETER_SC = '-p'
ARG_INPUT_SC = '-i'
SET_ALL = '-all'
SET_ALL_SC = '-a'

LAST_ACTIVE_SESSION = 'last_active_session'
LAST_ACTIVE_RECIPE = 'last_active_recipe'
LAST_ACTIVE_PROCESSES = 'last_active_processes'

DEFAULT_METAWOLF_STORAGE_PATH = '~/.metawolf'

CMD2_CMDS = [
  'alias', 'edit', 'run_pyscript', 'macro', 'run_script', 'shortcuts']

RECIPES = utils.MetawolfUtils('').GetRecipes().keys()

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
  def __init__(
      self,
      session_path: str = DEFAULT_METAWOLF_STORAGE_PATH,
      transcript_files: Optional[List[str]] = None,
      colored_prompt: bool = True,
  ) -> None:
    """Initialize Metawolf.

    Args:
      session_path (str): Optional. The path to the file in which session
          information should be stored. If not provided, defaults to
          '~/.metawolf'.
      transcript_files (List[str]): Optional. A list of paths to transcripts.
          This can be used to e.g. test end-to-end interactions with Metawolf.
      colored_prompt (bool): Optional. True if the prompt should be displayed
          with colors.
    """
    super(Metawolf, self).__init__(
        shortcuts=cmd2.DEFAULT_SHORTCUTS,
        allow_cli_args=not transcript_files,
        transcript_files=transcript_files)

    self.metawolf_output = output.MetawolfOutput()
    self.metawolf_utils = utils.MetawolfUtils(session_path)
    self.colored_prompt = colored_prompt

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
        ARG_RECIPE,
        'Recipe to use. Type `{0:s}` to see available recipes.'.format(
            self.metawolf_output.Color('show -rs[recipes]', output.YELLOW)),
        str)
    self.AddSessionSettable(self.recipe_settable)

    self.session_id_settable = session.SessionSettable(
        SESSION_ID_NOT_INITIALIZE,
        RECIPE_NAME_IGNORED,
        ARG_SESSION,
        'Metawolf\'s session_id. Type `{0:s}` to display existing '
        'sessions, and switch with `{1:s}`.'.format(
            self.metawolf_output.Color('show -s[essions]', output.YELLOW),
            self.metawolf_output.Color(
                'set -s[ession] session_id', output.YELLOW)
        ), str)
    self.AddSessionSettable(self.session_id_settable)

    self.sessions = self.LoadSession()
    self.recipes = self.metawolf_utils.GetRecipes()
    self.poutput(self.metawolf_output.Welcome())

    # Hide default cmd2 commands
    for c in CMD2_CMDS:
      self.hidden_commands.append(c)

  @property
  def recipe(self) -> Any:
    """Return recipe_settable's value."""
    return self.recipe_settable.GetValue()

  @property
  def session_id(self) -> Any:
    """Return session_settable's value."""
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
    """Create a new session."""
    session_id = utils.CreateNewSessionID()
    self.recipe_settable.SetValue(None)
    self.reload_settables = False
    self.copy_over = False
    self.ClearSessionSettables()
    self.SetSessionID(session_id)
    self.sessions[session_id] = {}
    # Remove auto-complete choices for the previous recipe
    for a in self.set_parser._actions:  # pylint: disable=protected-access
      if a.dest == 'p':
        a.choices = None
        break

  def do_ls(self, _: cmd2.Statement) -> None:
    """Print the current recipe and its arguments."""
    t = PrettyTable(['Name', 'Description', 'Type', 'Current Value'],
                    align='l')
    for _, settable in self.session_settables.items():  # type: ignore
      value = settable.GetValue()
      t.add_row(
        [self.metawolf_output.Color(settable.name, output.GREEN),
         settable.description,
         settable.type.__name__,
         self.metawolf_output.Color(
           value, output.GREEN) if value is not None else value
         ])
    self.poutput(t)

  set_parser = cmd2.Cmd2ArgumentParser(
    description='Set arguments in Metawolf.')
  set_parser.add_argument('-r', ARG_RECIPE, choices=RECIPES,
                          help='Set a recipe.')
  set_parser.add_argument('-s', ARG_SESSION, type=str,
                          help='Set a session.')
  set_parser.add_argument('-a', '-all', action='store_true',
                          help='Set all arguments of the current recipe.')
  set_parser.add_argument('-p', ARG_PARAMETER, type=str,
                          help='Set a recipe argument.')
  @cmd2.with_argparser(set_parser, with_unknown_args=True)  # type: ignore
  # pylint: disable=arguments-differ
  def do_set(self, args: argparse.Namespace, _: Any) -> None:
    """Set arguments for Metawolf.

    Args:
      args (argparse.Namespace): The arguments from the user's input.
    """

    if not args.cmd2_statement.get():
      self.do_ls(_)
      return

    what =  shlex.split(args.cmd2_statement.get())

    if what[0] in [SET_ALL, SET_ALL_SC]:
      if not self.recipe:
        self.poutput('Please set a recipe first: `{0:s}`'.format(
            self.metawolf_output.Color(
                'set -r[ecipe] recipe_name', output.YELLOW)))
        return
      for settable in self.session_settables.values():
        if settable.recipe == RECIPE_NAME_IGNORED:
          # Session and recipe settables are not in scope.
          continue
        try:
          value = input('Set value for{0:s}parameter {1:s} ({2:s}: {3:s}. '
                        'Press "enter" to skip or ctrl+d to abort.): '.format(
            ' ({0:s}) '.format(self.metawolf_output.Color(
              'optional',
              output.YELLOW,
              escape=True)) if settable.IsOptional() else ' ',
            settable.name,
            self.metawolf_output.Color(
                'Current value', output.YELLOW, escape=True),
            self.metawolf_output.Color(
                settable.GetValue(), output.GREEN, escape=True)))
        except EOFError:
          # User aborted with ctrl+d
          self.poutput('')
          return
        value = str(value).strip()
        if not value:
          continue
        updated = self.UpdateSessionSettable(value, settable=settable)
        while not updated:
          try:
            value = input('Set value for parameter {0:s} ({1:s}: {2:s}. Press '
                          '"enter" to skip or ctrl+d to abort.): '.format(
              settable.name,
              self.metawolf_output.Color(
                  'Current value', output.YELLOW, escape=True),
              self.metawolf_output.Color(
                  settable.GetValue(), output.GREEN, escape=True)))
          except EOFError:
            # User aborted with ctrl+d
            self.poutput('')
            return
          value = str(value).strip()
          if not value:
            break
          updated = self.UpdateSessionSettable(value, settable=settable)
      return

    if what[0] in [ARG_SESSION, ARG_SESSIONS_SC]:
      session_id = what[1]
      if session_id not in self.sessions:
        self.poutput(self.metawolf_output.Color(
            'Session {0:s} does not exist.'.format(session_id), output.RED))
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

    if what[0] in [ARG_RECIPE, ARG_RECIPE_SC]:
      recipe = what[1]
      if recipe not in self.recipes:
        self.poutput(self.metawolf_output.Color(
            'Recipe {0:s} does not exist.'.format(recipe), output.RED))
        return

      if self.recipe:
        # If a recipe is already set, prompt the user for copy over option
        value = input('Would you like to copy over previous recipe ({0:s}) '
                      'arguments to the new recipe ({1:s}): [yN]? '.format(
            self.recipe, recipe)) or 'n'
        copy_over = utils.Str2Bool(str(value))
        while copy_over not in [False, True]:
          value = input('[yN]? ') or 'n'
          copy_over = utils.Str2Bool(str(value))
        self.copy_over = copy_over

      if self.recipe != recipe:
        # Recipe changed, we need to reload the settables.
        self.reload_settables = True

      self.recipe_settable.SetValue(recipe)
      self.poutput('To see arguments for this recipe, type {0:s}. To set them'
                   ' interactively, type {1:s}'.format(
        self.metawolf_output.Color('set', output.YELLOW),
        self.metawolf_output.Color('set -a[ll]', output.YELLOW)))

    if what[0] in [ARG_PARAMETER, ARG_PARAMETER_SC]:
      s_id = None
      if self.session_id:
        if self.recipe:
          s_id = '{0:s}-{1:s}-{2:s}'.format(
              self.session_id, self.recipe, what[1])
        else:
          self.poutput('You must set a recipe first: `{0:s}`'.format(
            self.metawolf_output.Color(
              'set -r[ecipe] name', output.YELLOW)))
          return
      if s_id in self.session_settables and len(what) > 2:
        _ = self.UpdateSessionSettable(what[2], s_id=s_id)
      else:
        self.poutput(self.metawolf_output.Color(
          'You must specify a value for this parameter.', output.RED))

  def do_run(self, _: cmd2.Statement) -> None:
    """Run a DFTimewolf recipe. Show running recipes: `show -rn[running]`.

    This will run whatever recipe is currently being used in the session."""
    if not self.session_id or not self.recipe:
      self.poutput(self.metawolf_output.Color(
          'No session/recipe detected, nothing to run.', output.RED))
      return

    cmd = self.metawolf_utils.PrepareDFTimewolfCommand(
        self.recipe, self.session_settables)
    if not cmd:
      self.poutput(
          'Some parameters are missing. Type `{0:s}` to see which parameter '
          'you need to set and their current values.'.format(
              self.metawolf_output.Color('set', output.YELLOW)))
      return

    value = input('Confirm running: {0:s} [yN]? '.format(
        self.metawolf_output.Color(' '.join(['dftimewolf'] + cmd[1:]),
                                   output.YELLOW, escape=True))) or 'n'
    ans = utils.Str2Bool(str(value))
    while ans not in [False, True]:
      value = input('[yN]? ') or 'n'
      ans = utils.Str2Bool(str(value))
    if not ans:
      return

    self.poutput('Running: {0:s}'.format(
        self.metawolf_output.Color(' '.join(cmd), output.YELLOW)))
    self.poutput('To see past and current runs, type {0:s}.'.format(
      self.metawolf_output.Color('`show -rn[running]`', output.YELLOW)))

    metawolf_process = output.MetawolfProcess(
        session_id=self.session_id,
        cmd=cmd,
        output_id=self.nb_running_processes,
        metawolf_utils=self.metawolf_utils)
    metawolf_process.Run()

    self.processes.append(metawolf_process)
    self.nb_running_processes += 1

  show_parser = cmd2.Cmd2ArgumentParser(
    description='Show sessions, recipes, runs and outputs.')
  show_parser.add_argument('-s', ARG_SESSIONS, action='store_true',
                           help='Show metawolf sessions.')
  show_parser.add_argument('-r', ARG_RECIPE, choices=RECIPES,
                           help='Show details about a single recipe.')
  show_parser.add_argument('-rs', ARG_RECIPES, action='store_true',
                           help='Show all recipes available.')
  show_parser.add_argument('-rn', ARG_RUNNING, action='store_true',
                           help='Show past and current recipe runs.')
  show_parser.add_argument('-o', ARG_OUTPUT, nargs='?', type=int,
                           help='Show the output of a recipe run.')
  @cmd2.with_argparser(show_parser)
  def do_show(self, args: argparse.Namespace) -> None:
    """Show sessions, recipes, runs and outputs. `help show` for details.

    Possible choices: [`-recipes`, `-recipe recipe_name`, `-sessions`,
    `-running`, `-output output_id`]. `recipes` shows the user the available
    DFTimewolf recipes, while `recipe recipe_name` shows the details of a
    given recipe. `sessions` shows the currently available Metawolf sessions
    and any recipe in use, along with information about the recipe's state.
    `running` displays running jobs and their state. `output output_id` writes
    the output of the matching output_id to STDOUT. Autocomplete is available.

    Args:
      args: Arguments from the command line.
    """
    if not args.cmd2_statement.get():
      self.poutput('Usage of show (autocompletion is enabled.): `{0:s}`'.format(
          self.metawolf_output.Color(
              'show [-rs[recipes], -r[ecipe] recipe_name, -s[essions], '
              '-rn[running], -o[utput] output_id].', output.YELLOW)))
      return

    if args.cmd2_statement.get() in [ARG_RECIPES, ARG_RECIPES_SC]:
      t = PrettyTable(['Name', 'Description'], align='l')
      for recipe_name, recipe_desc in self.recipes.items():
        t.add_row([
            self.metawolf_output.Color(recipe_name, output.GREEN),
            recipe_desc])
      self.poutput(t)
      return

    if args.cmd2_statement.get() in [ARG_SESSIONS, ARG_SESSIONS_SC]:
      t = PrettyTable(
          ['Session ID (`{0:s}` or `{1:s}`)'.format(
              self.metawolf_output.Color('new', output.YELLOW),
            self.metawolf_output.Color(
                'set -s[ession] session', output.YELLOW)),
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
        for recipe in active_recipes:
          statuses[recipe] = ('', '')
          for metawolf_process in self.processes:
            # pylint: disable=line-too-long
            if s_id == metawolf_process.session_id and metawolf_process.recipe == recipe:
              # pylint: enable=line-too-long
              statuses[recipe] = (
                  metawolf_process.Status(),
                  metawolf_process.timestamp_readable or ''
              )  # latest status of recipe run
        session_iter = self.metawolf_output.Color(s_id, output.GREEN)
        if self.session_id in session_iter:
          session_iter = '{0:s}{1:s}'.format(
              session_iter, self.metawolf_output.Color(' <--', output.YELLOW))
        sortedStatues = {key:statuses[key] for key in sorted(statuses)}
        t.add_row(
            [session_iter,
             '\n'.join(sorted(active_recipes)),
             '\n'.join([s for s, _ in sortedStatues.values()]),
             '\n'.join([t for _, t in sortedStatues.values()])])
      self.poutput(t)
      return

    if args.cmd2_statement.get() in [ARG_RUNNING, ARG_RUNNING_SC]:
      table = PrettyTable(
        ['Session ID',
         'Command ID',
         'Output ID',
         'Timestamp (UTC)',
         'Command',
         'Status'],
        align='l')
      for metawolf_process in self.processes:
        table.add_row(
            [metawolf_process.session_id,
             metawolf_process.cmd_id,
             metawolf_process.output_id,
             metawolf_process.timestamp_readable,
             metawolf_process.cmd_readable,
             metawolf_process.Status()])
      self.poutput(table)
      return

    # Otherwise, check if we show an output or a recipe details
    user_input = args.cmd2_statement.get().split(' ')
    action = user_input[0]
    if len(user_input) != 2 and action in [ARG_RECIPE, ARG_RECIPE_SC]:
      # Malformed command, do nothing.
      self.poutput(
          'Malformed command. Type `{0:s}` to see available options.'.format(
              self.metawolf_output.Color('show', output.YELLOW)))
      return

    if action in [ARG_RECIPE, ARG_RECIPE_SC]:
      value = user_input[1]
      df_recipe = self.metawolf_utils.recipe_manager.Recipes().get(value)
      if not df_recipe:
        self.poutput(self.metawolf_output.Color(
            'Recipe {0!s} does not exist.'.format(value), output.RED))
        return

      # Recipe description
      t = PrettyTable(
          [self.metawolf_output.Color(df_recipe.name, output.GREEN)], align='l')
      t.add_row([df_recipe.description])
      self.poutput(t)

      # Recipe's arguments
      t = PrettyTable(
          ['Argument', 'Description'],
          align='l')
      for name, desc in [(a.switch, a.help_text) for a in df_recipe.args]:
        is_optional = name.startswith('--')
        if is_optional:
          name = name.replace('--', '')
          desc = self.metawolf_output.Color(
              '[Optional]. ', output.YELLOW) + desc
        t.add_row([self.metawolf_output.Color(name, output.GREEN), desc])
      self.poutput(t)
      return

    def read_output(process: output.MetawolfProcess) -> None:
      out = process.Read()
      if out:
        print(out)

    if action in [ARG_OUTPUT, ARG_OUTPUT_SC]:
      if not self.processes:
        return
      if len(user_input) < 2:
        # No output ID provided, output latest run.
        last_run_process = max(
          self.processes, key=lambda p: p.output_id)
        if last_run_process:
          read_output(last_run_process)
          return
        # Else display running processes
        self.poutput(self.metawolf_output.Color(
          'No output found. Showing (previous) runs:', output.YELLOW))
        self.do_show(cmd2.Statement(ARG_RUNNING))
        return
      value = user_input[1]
      for metawolf_process in self.processes:
        if value == str(metawolf_process.output_id):
          read_output(metawolf_process)

  send_parser = cmd2.Cmd2ArgumentParser(
      description='Communicate with running recipes.')
  send_parser.add_argument('-o', ARG_OUTPUT, nargs='?', type=int,
                           help='The output ID of the process to communicate '
                                'with.')
  send_parser.add_argument('-i', ARG_INPUT, type=str,
                           help='The input to send to the process\' STDIN.'
                                'Input must be between quotes.')
  @cmd2.with_argparser(send_parser)
  def do_send(self, args: argparse.Namespace) -> None:
    """Communicate with running recipes.

    Args:
      args (argparse.Namespace): The user's input.
    """
    if not args.cmd2_statement.get():
      self.poutput('Usage of send: `{0:s}`. This will send <input> to the '
                   'STDIN of the process with output ID <output_id>.'.format(
        self.metawolf_output.Color(
          'send [-i[nput] input -o[utput] output_id].',
          output.YELLOW)))
      return
    user_input = shlex.split(args.cmd2_statement.get())
    if len(user_input) != 4:
      self.poutput('Usage of send: `{0:s}`. This will send "<input>" to the '
                   'STDIN of the process with output ID <output_id>.'.format(
        self.metawolf_output.Color(
          'send [-i[nput] input -o[utput] output_id].',
          output.YELLOW)))
      return
    action = user_input[0]
    if action not in [ARG_INPUT, ARG_INPUT_SC]:
      return
    action = user_input[2]
    if action not in [ARG_OUTPUT, ARG_OUTPUT_SC]:
      return
    inp = str(user_input[1])
    output_id = user_input[3]
    for metawolf_process in self.processes:
      if output_id == str(metawolf_process.output_id):
        metawolf_process.Send(inp)

  def do_reload(self, _: cmd2.Statement) -> None:
    """Reload the default recipe arguments."""
    self.reload_settables = True
    self.reload_default = True

  def do_clear(self, _: cmd2.Statement) -> None:
    """Clear the screen."""
    self.do_shell('clear')

  def do_clean(self, _: cmd2.Statement) -> None:
    """Clean the processes associated to the current session.

    - Delete output files
    - Remove metawolf's runs from session file
    - Reset output counter"""
    for metawolf_process in self.processes:
      if metawolf_process.Poll() is None:
        termination_msg = metawolf_process.Terminate()
        if termination_msg:
          self.poutput(termination_msg)
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
      self.poutput(self.metawolf_output.Color(
          'Usage of kill: `kill command_id`.', output.YELLOW))
      return

    for metawolf_process in self.processes:
      if metawolf_process.cmd_id == st.args:
        termination_msg = metawolf_process.Terminate()
        if termination_msg:
          self.poutput(termination_msg)
        break

  def do_quit(self, _: argparse.Namespace) -> Optional[bool]:
    """Quit Metawolf.

    Returns:
      Optional[bool]: True if the shell should be stopped.
    """
    if not utils.RunInBackground(self.processes):
      # Close any open files / terminate running processes
      for metawolf_process in self.processes:
        termination_msg = metawolf_process.Terminate()
        if termination_msg and metawolf_process.Poll() is None:
          self.poutput(termination_msg)
    return super(Metawolf, self).do_quit(_)  # type: ignore

  def do_exit(self, _: argparse.Namespace) -> Optional[bool]:
    """Exit Metawolf.

    Returns:
      Optional[bool]: True if the shell should be stopped.
    """
    return self.do_quit(_)

  def sigint_handler(self, signum: int, _: FrameType) -> None:
    """Handle SIGINT.

    Args:
      signum (int): Signal number.
    """

    if signum == signal.SIGINT:
      if not utils.RunInBackground(self.processes):
        # Close any open files / terminate running processes
        for metawolf_process in self.processes:
          termination_msg = metawolf_process.Terminate()
          if termination_msg:
            self.poutput(termination_msg)
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
      session_id = utils.CreateNewSessionID()
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
          proc = output.MetawolfProcess(
              from_dict=metawolf_process, metawolf_utils=self.metawolf_utils)
          self.processes.append(proc)
        continue
      for settable_id, settable in settables.items():
        s_id = '{0:s}-{1:s}-{2:s}'.format(
            self.session_id, self.recipe, settable.name)
        if settable_id == s_id and settable_id not in self.session_settables:
          self.AddSessionSettable(settable)
        # Restore auto-complete choices for the current recipe
        if recipe in [last_recipe, self.recipe]:
          for a in self.set_parser._actions:  # pylint: disable=protected-access
            if a.dest == 'p':
              if not a.choices:
                a.choices = []
              a.choices.append(settable.name)  # type: ignore
              break

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
          current_sessions[self.session_id][self.recipe][settable_id] = utils.Marshal(settable)
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

    with open(os.path.expanduser(self.metawolf_utils.session_path), 'w') as f:
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
    # Readline needs escaping around invisible characters
    prompt = '\001' + prompt + '\002'
    # self.prompt is inherited from cmd2
    # pylint: disable=attribute-defined-outside-init
    if self.colored_prompt:
      self.prompt = prompt
    else:
      self.prompt = cmd2_ansi.strip_style(prompt)
    # pylint: enable=attribute-defined-outside-init

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
    recipes = self.metawolf_utils.recipe_manager.Recipes()
    for arg in recipes[self.recipe].args:
      name = arg.switch
      desc = arg.help_text
      default_value = arg.default

      t = type(default_value) if default_value is not None else str
      is_optional = name.startswith('--')
      if is_optional:
        name = name.replace('--', '')
        desc = self.metawolf_output.Color('[Optional]. ', output.YELLOW) + desc
      s_id = '{0:s}-{1:s}-{2:s}'.format(self.session_id, self.recipe, name)
      if s_id not in self.session_settables or self.reload_default:
        current_settable = current_sessions.get(self.session_id, {}).get(
            self.recipe, {}).get(s_id)
        if current_settable:
          if not self.reload_default:
            session_settable = current_settable
          else:
            # Display reset attributes to the user
            session_settable = session.SessionSettable(
              self.session_id, self.recipe, name, desc, t,
              optional=is_optional)
            session_settable.SetValue(default_value)
            out = self.metawolf_output.Color(
              '{0:s}: '.format(current_settable.name), output.YELLOW)
            out += self.metawolf_output.Color(
              current_settable.GetValue(), output.RED)
            out += ' --> '
            out += self.metawolf_output.Color(default_value, output.GREEN)
            if current_settable.GetValue() != default_value:
              self.poutput(out)
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
    # Add the recipe arguments to the autocomplete parser
    for action in self.set_parser._actions:  # pylint: disable=protected-access
      if action.dest == 'p':
        action.choices = [args.switch.replace('--', '') for args in
                          recipes[self.recipe].args]
        break

    # Recipes just reloaded, so we can turn this off.
    self.reload_settables = False
    self.reload_default = False
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
          s_id must be.

    Returns:
      bool: True if the settable was correctly updated, False otherwise.
    """
    if not s_id and not settable:
      return False

    settable = self.session_settables.get(s_id) if s_id else settable
    if not settable:
      return False

    prev_value = settable.GetValue()
    value = utils.CastToType(updated_value, settable.type)
    if value is None:
      input_type = utils.GetType(updated_value)
      self.poutput(self.metawolf_output.Color(
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
    self.poutput(out)
    return True

  def ClearSessionSettables(self) -> None:
    """Clear current settables."""
    to_remove = []
    for _, settable in self.session_settables.items():
      if settable.name not in [ARG_RECIPE, ARG_SESSION]:
        to_remove.append(settable)
    for settable in to_remove:
      self.RemoveSessionSettable(settable)


if __name__ == "__main__":
  sys.exit(Metawolf().cmdloop())
