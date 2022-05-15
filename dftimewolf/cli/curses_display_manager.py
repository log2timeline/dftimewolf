# -*- coding: utf-8 -*-
"""Curses output management class."""

from enum import Enum
import threading
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union

import curses

class Status(Enum):
  """Enum class for module states."""
  PENDING = 'Pending'
  SETTINGUP = "Setting Up"
  RUNNING = 'Running'
  PREPROCESSING = 'Preprocessing'  # used for threaded modules
  PROCESSING = 'Processing'  # used for threaded modules
  POSTPROCESSING = 'Postprocessing'  # used for threaded modules
  COMPLETED = 'Completed'
  ERROR = 'Error'


class Module:
  """An object used by the CursesDisplayManager used to represent a DFTW module.
  """
  name: str = ''
  runtime_name: str = ''
  status: Status = Status.PENDING
  dependencies: List[str] = []
  error_module_line: str = ''
  threads: Dict[str, Dict[str, Any]] = {}
  threads_containers_max: int = 0
  threads_containers_completed: int = 0

  def __init__(self,
               name: str,
               dependencies: List[str],
               runtime_name: Optional[str]):
    """Initialise the Module object."""
    self.name = name
    self.runtime_name = runtime_name if runtime_name else name
    self.dependencies = dependencies

  def Stringify(self) -> List[str]:
    """Returns an CursesDisplayManager friendly string describing the module."""
    module_line = f'    {self.runtime_name}: {self.status.value}'
    thread_lines = []

    if self.status == Status.PENDING and len(self.dependencies):
      module_line += f' ({", ".join(self.dependencies)})'
    elif self.status == Status.ERROR and self.error_module_line:
      module_line += f': {self.error_module_line}'
    elif self.status in [Status.RUNNING, Status.PROCESSING] and self.threads:
      module_line += (f' - {self.threads_containers_completed} of '
          f'{self.threads_containers_max} containers completed')
      for n, t in self.threads.items():
        thread_lines.append(
            f'      {n}: {t["status"].value} ({t["container"]})')

    return [module_line] + thread_lines


class Message:
  """Helper class for managing messages."""
  source: str = ''
  content: str = ''
  is_error: bool = False  # used for colouring, maybe

  def __init__(self, source: str, content: str, is_error: bool = False) -> None:
    """Initialise a module_line object."""
    self.source = source
    self.content = content
    self.is_error = is_error

  def Stringify(self, source_buff_len: int = 0) -> str:
    """Returns an CursesDisplayManager friendly string of the module_line."""
    pad = (len(self.source) if len(self.source) > source_buff_len
        else source_buff_len)

    return f'[ {self.source:{pad}} ] {self.content}'


class CursesDisplayManager:
  """Handles the curses based console output, based on information passed in.
  """

  def __init__(self) -> None:
    """Intiialises the CursesDisplayManager, including setting up curses."""
    self.recipe_name: str = ''
    self.exception: Union[Exception, None] = None
    self.preflights: Dict[str, Module] = {}
    self.modules: Dict[str, Module] = {}
    self.messages: List[Message] = []
    self.lock = threading.Lock()

    self.stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    self.stdscr.keypad(True)

  def SetRecipe(self, recipe: str) -> None:
    """Set the recipe name."""
    self.recipe_name = recipe

  def SetException(self, e: Exception) -> None:
    """Set a Exception to be included in the display."""
    self.exception = e

  def EnqueueMessage(self, m: Message) -> None:
    """Enqueue a message to be displayed."""
    self.messages.append(m)
    self.Draw()

  def EnqueuePreflight(self,
                       name: str,
                       dependencies: List[str],
                       runtime_name: Optional[str]) -> None:
    """Enqueue a preflight module object for display."""
    m = Module(name, dependencies, runtime_name)
    self.preflights[m.runtime_name] = m

  def EnqueueModule(self,
                       name: str,
                       dependencies: List[str],
                       runtime_name: Optional[str]) -> None:
    """Enqueue a module object for display."""
    m = Module(name, dependencies, runtime_name)
    self.modules[m.runtime_name] = m

  def UpdateModuleState(self, module: str, status: Status) -> None:
    """Update the state of a module for display."""
    if module in self.preflights:
      self.preflights[module].status = status
    if module in self.modules:
      self.modules[module].status = status

    self.Draw()

  def SetThreadedModuleContainerCount(self, module: str, count: int) -> None:
    """Set the container count that a threaded module will operate on."""
    if module in self.preflights:
      self.preflights[module].threads_containers_max = count
    if module in self.modules:
      self.modules[module].threads_containers_max = count

  def UpdateModuleThreadState(self,
                              module: str,
                              status: Status,
                              thread: str,
                              container: str) -> None:
    """Update the state of a thread within a threaded module for display."""
    if module in self.preflights:
      self.preflights[module].threads[thread] = {'status': status,
                                                 'container': container}
      if status == Status.COMPLETED:
        self.preflights[module].threads_containers_completed += 1
    if module in self.modules:
      self.modules[module].threads[thread] = {'status': status,
                                              'container': container}
      if status == Status.COMPLETED:
        self.modules[module].threads_containers_completed += 1

    self.Draw()

  def Draw(self) -> None:
    """Draws the window."""
    with self.lock:
      self.stdscr.clear()
      x, _ = self.stdscr.getmaxyx()

      curr_line = 0

      self.stdscr.addstr(curr_line, 0, self.recipe_name)
      curr_line += 1
      self.stdscr.addstr(curr_line, 0, '  Preflights:')
      curr_line += 1

      for _, module in self.preflights.items():
        for line in module.Stringify():
          self.stdscr.addstr(curr_line, 0, line)
          curr_line += 1

      self.stdscr.addstr(curr_line, 0, '  Modules:')
      curr_line += 1

      for _, module in self.modules.items():
        for line in module.Stringify():
          self.stdscr.addstr(curr_line, 0, line)
          curr_line += 1

      curr_line += 1
      self.stdscr.addstr(curr_line, 0, 'Messages:')
      curr_line += 1

      module_line_source_len = 0
      for m in self.messages:
        if len(m.source) > module_line_source_len:
          module_line_source_len = len(m.source)

      for m in self.messages[::-1]:
        self.stdscr.addstr(
            curr_line, 0, f'  {m.Stringify(module_line_source_len)}')
        curr_line += 1

        if curr_line > x - 3:
          break

      if self.exception:
        self.stdscr.addstr(x - 2, 0,
            f'Exception encountered: {self.exception.__str__()}')

      self.stdscr.refresh()

  def CleanUp(self) -> None:
    """Curses finalisation actions."""
    curses.nocbreak()
    self.stdscr.keypad(False)
    curses.echo()
    curses.endwin()

  def PrintMessages(self) -> None:
    """Dump all messages to stdout. Intended to be used when exiting, after
    removing the curses window."""

    if self.messages:
      print('Messages:')
      module_line_source_len = 0
      for m in self.messages:
        if len(m.source) > module_line_source_len:
          module_line_source_len = len(m.source)

      for m in self.messages:
        print(f'  {m.Stringify(module_line_source_len)}')

    if self.exception:
      traceback.print_exception(None,
                                self.exception,
                                self.exception.__traceback__)

  def Pause(self) -> None:
    """Ask the user to press any key to continue."""
    with self.lock:
      x, _ = self.stdscr.getmaxyx()

      self.stdscr.addstr(x - 1, 0, "Press any key to continue")
      self.stdscr.getkey()
      self.stdscr.addstr(x - 1, 0, "                         ")
