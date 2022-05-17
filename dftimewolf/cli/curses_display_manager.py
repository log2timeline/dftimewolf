# -*- coding: utf-8 -*-
"""Curses output management class."""

from enum import Enum
import os
import sys
import threading
import traceback
from typing import Any, Dict, List, Optional, Union

import curses

class Status(Enum):
  """Enum class for module states."""
  PENDING = 'Pending'
  SETTINGUP = "Setting Up"
  RUNNING = 'Running'
  PREPROCESSING = 'Preprocessing'  # used for threaded _modules
  PROCESSING = 'Processing'  # used for threaded _modules
  POSTPROCESSING = 'Postprocessing'  # used for threaded _modules
  COMPLETED = 'Completed'
  ERROR = 'Error'
  CANCELLED = 'Cancelled'


class Module:
  """An object used by the CursesDisplayManager used to represent a DFTW module.
  """
  name: str = ''
  runtime_name: str = ''
  status: Status = Status.PENDING
  dependencies: List[str] = []
  error_message: str = ''
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
    module_line = f'     {self.runtime_name}: {self.status.value}'
    thread_lines = []

    if self.status == Status.PENDING and len(self.dependencies):
      module_line += f' ({", ".join(self.dependencies)})'
    elif self.status == Status.ERROR and self.error_message:
      module_line += f': {self.error_message}'
    elif self.status in [Status.RUNNING, Status.PROCESSING] and self.threads:
      module_line += (f' - {self.threads_containers_completed} of '
          f'{self.threads_containers_max} containers completed')
      for n, t in self.threads.items():
        thread_lines.append(
            f'       {n}: {t["status"].value} ({t["container"]})')

    return [module_line] + thread_lines


class Message:
  """Helper class for managing _messages."""
  source: str = ''
  content: str = ''
  is_error: bool = False  # used for colouring, maybe

  def __init__(self, source: str, content: str, is_error: bool = False) -> None:
    """Initialise a Message object."""
    self.source = source
    self.content = content
    self.is_error = is_error

  def Stringify(self, source_buff_len: int = 0) -> str:
    """Returns an CursesDisplayManager friendly string of the Message."""
    pad = (len(self.source) if len(self.source) > source_buff_len
        else source_buff_len)

#    colour_code = '\u001b[31m' if self.is_error else ''
#    reset_code = '\u001b[0m' if self.is_error else ''
#
#    return f'[ {self.source:{pad}} ] {colour_code}{self.content}{reset_code}'
    return f'[ {self.source:{pad}} ] {self.content}'

class CursesDisplayManager:
  """Handles the curses based console output, based on information passed in.
  """

  def __init__(self) -> None:
    """Intiialises the CursesDisplayManager."""
    self._recipe_name: str = ''
    self._exception: Union[Exception, None] = None
    self._preflights: Dict[str, Module] = {}
    self._modules: Dict[str, Module] = {}
    self._messages: List[Message] = []
    self._messages_longest_source_len: int = 0
    self._lock = threading.Lock()
    self.stdscr = None

  def StartCurses(self) -> None:
    """Call the curses initialisation methods."""
    self.stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    self.stdscr.keypad(True)

  def EndCurses(self):
    """Curses finalisation actions."""
    if True in [m.is_error for m in self._messages] or self._exception:
      self.Pause()

    if not self.stdscr:
      return

    curses.nocbreak()
    self.stdscr.keypad(False)
    curses.echo()
    curses.endwin()

  def SetRecipe(self, recipe: str) -> None:
    """Set the recipe name."""
    self._recipe_name = recipe

  def SetException(self, e: Exception) -> None:
    """Set a Exception to be included in the display."""
    self._exception = e

  def SetError(self, module: str, message: str) -> None:
    """Sets the error state ane message for a module."""
    if module in self._preflights:
      self._preflights[module].error_message = message
      self._preflights[module].status = Status.ERROR
    if module in self._modules:
      self._modules[module].error_message = message
      self._modules[module].status = Status.ERROR

    self.EnqueueMessage(module, message, True)

    self.Draw()

  def EnqueueMessage(self,
                     source: str,
                     content: str,
                     is_error: bool = False) -> None:
    """Enqueue a message to be displayed."""
    if self._messages_longest_source_len < len(source):
      self._messages_longest_source_len = len(source)
    self._messages.append(Message(source, content, is_error))
    self.Draw()

  def EnqueuePreflight(self,
                       name: str,
                       dependencies: List[str],
                       runtime_name: Optional[str]) -> None:
    """Enqueue a preflight module object for display."""
    m = Module(name, dependencies, runtime_name)
    self._preflights[m.runtime_name] = m

  def EnqueueModule(self,
                       name: str,
                       dependencies: List[str],
                       runtime_name: Optional[str]) -> None:
    """Enqueue a module object for display."""
    m = Module(name, dependencies, runtime_name)
    self._modules[m.runtime_name] = m

  def UpdateModuleState(self, module: str, status: Status) -> None:
    """Update the state of a module for display."""
    if module in self._preflights:
      if self._preflights[module].status != Status.ERROR:
        self._preflights[module].status = status
    if module in self._modules:
      if self._modules[module].status != Status.ERROR:
        self._modules[module].status = status

    self.Draw()

  def SetThreadedModuleContainerCount(self, module: str, count: int) -> None:
    """Set the container count that a threaded module will operate on."""
    if module in self._preflights:
      self._preflights[module].threads_containers_max = count
    if module in self._modules:
      self._modules[module].threads_containers_max = count

  def UpdateModuleThreadState(self,
                              module: str,
                              status: Status,
                              thread: str,
                              container: str) -> None:
    """Update the state of a thread within a threaded module for display."""
    if module in self._preflights:
      self._preflights[module].threads[thread] = {'status': status,
                                                 'container': container}
      if status == Status.COMPLETED:
        self._preflights[module].threads_containers_completed += 1
    if module in self._modules:
      self._modules[module].threads[thread] = {'status': status,
                                              'container': container}
      if status == Status.COMPLETED:
        self._modules[module].threads_containers_completed += 1

    self.Draw()

  def Draw(self) -> None:
    """Draws the window."""
    if not self.stdscr:
      return

    with self._lock:
      self.stdscr.clear()
      y, x = self.stdscr.getmaxyx()

      curr_line = 1

      self.stdscr.addstr(curr_line, 0, f' {self._recipe_name}')
      curr_line += 1

      if self._preflights:
        self.stdscr.addstr(curr_line, 0, '   Preflights:')
        curr_line += 1
        for _, module in self._preflights.items():
          for line in module.Stringify():
            self.stdscr.addstr(curr_line, 0, line)
            curr_line += 1

      self.stdscr.addstr(curr_line, 0, '   Modules:')
      curr_line += 1
      for _, module in self._modules.items():
        for line in module.Stringify():
          self.stdscr.addstr(curr_line, 0, line)
          curr_line += 1

      curr_line += 1
      self.stdscr.addstr(curr_line, 0, ' Messages:')
      curr_line += 1

      for m in self._messages[::-1]:
        self.stdscr.addstr(
            curr_line, 0, f'  {m.Stringify(self._messages_longest_source_len)}')
        curr_line += 1

        if curr_line > y - 4:
          break

      if self._exception:
        self.stdscr.addstr(y - 2, 0,
            f' Exception encountered: {self._exception.__str__()}')

      self.stdscr.move(curr_line, 0)
      self.stdscr.refresh()

  def PrintMessages(self) -> None:
    """Dump all _messages to stdout. Intended to be used when exiting, after
    removing the curses window."""

    if self._messages:
      for m in self._messages:
        print(f'  {m.Stringify(self._messages_longest_source_len)}')

    if self._exception:
      traceback.print_exception(None,
                                self._exception,
                                self._exception.__traceback__)

  def Pause(self) -> None:
    """Ask the user to press any key to continue."""
    with self._lock:
      x, _ = self.stdscr.getmaxyx()

      self.stdscr.addstr(x - 1, 0, "Press any key to continue")
      self.stdscr.getkey()
      self.stdscr.addstr(x - 1, 0, "                         ")
