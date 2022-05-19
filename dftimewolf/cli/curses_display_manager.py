# -*- coding: utf-8 -*-
"""Curses output management class."""

from enum import Enum
import threading
import traceback
from typing import Any, Dict, List, Optional, Union

import curses

class Status(Enum):
  """Enum class for module states.

  The order here is important, as it's the order modules will be displayed."""
  COMPLETED = 'Completed'
  SETTINGUP = 'Setting Up'
  ERROR = 'Error'
  RUNNING = 'Running'
  PREPROCESSING = 'Preprocessing'
  PROCESSING = 'Processing'
  POSTPROCESSING = 'Postprocessing'
  PENDING = 'Pending'
  CANCELLED = 'Cancelled'


class Module:
  """An object used by the CursesDisplayManager used to represent a DFTW module.
  """
  name: str = ''
  runtime_name: str = ''
  status: Status = Status.PENDING
  _dependencies: List[str] = []
  _error_message: str = ''
  _threads: Dict[str, Dict[str, Union[Status, str]]] = {}
  _threads_containers_max: int = 0
  _threads_containers_completed: int = 0

  def __init__(self,
               name: str,
               dependencies: List[str],
               runtime_name: Optional[str]):
    """Initialise the Module object."""
    self.name = name
    self.runtime_name = runtime_name if runtime_name else name
    self._dependencies = dependencies

  def Stringify(self) -> List[str]:
    """Returns an CursesDisplayManager friendly string describing the module."""
    module_line = f'     {self.runtime_name}: {self.status.value}'
    thread_lines = []

    if self.status == Status.PENDING and len(self._dependencies):
      module_line += f' ({", ".join(self._dependencies)})'
    elif self.status == Status.ERROR:
      module_line += f': {self._error_message}'
    elif self.status in [Status.RUNNING, Status.PROCESSING] and self._threads:
      module_line += (f' - {self._threads_containers_completed} of '
          f'{self._threads_containers_max} containers completed')
      for n, t in self._threads.items():
        thread_lines.append(
            f'       {n}: {t["status"].value} ({t["container"]})')

    return [module_line] + thread_lines

  def SetStatus(self, status: Status) -> None:
    """Set the status of the module."""
    if self.status not in [Status.ERROR, Status.COMPLETED, Status.CANCELLED]:
      self.status = status  

  def SetThreadState(self, thread: str, status: Status, container: str) -> None:
    """Set the state of a thread within a threaded module."""
    self._threads[thread] = {'status': status,
                             'container': container}
    if status == Status.COMPLETED:
      self._threads_containers_completed += 1

  def SetError(self, message: str) -> None:
    """Sets the error for the module."""
    self._error_message = message
    self.status = Status.ERROR

  def SetContainerCount(self, count: int) -> None:
    """Sets the maximum container count for the module."""
    self._threads_containers_max = count


class Message:
  """Helper class for managing messages."""
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

    self.stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    self.stdscr.keypad(True)

  def EndCurses(self) -> None:
    """Curses finalisation actions."""
    if True in [m.is_error for m in self._messages] or self._exception:
      self.Pause()

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
      self._preflights[module].SetError(message)
    if module in self._modules:
      self._modules[module].SetError(message)

    self.EnqueueMessage(module, message, True)

    self.Draw()

  def EnqueueMessage(self,
                     source: str,
                     content: str,
                     is_error: bool = False) -> None:
    """Enqueue a message to be displayed."""
    if self._messages_longest_source_len < len(source):
      self._messages_longest_source_len = len(source)

    for line in content.split('\n'):
      if line:
        self._messages.append(Message(source, line, is_error))

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
      self._preflights[module].SetStatus(status)
    if module in self._modules:
      self._modules[module].SetStatus(status)

    self.Draw()

  def SetThreadedModuleContainerCount(self, module: str, count: int) -> None:
    """Set the container count that a threaded module will operate on."""
    if module in self._preflights:
      self._preflights[module].SetContainerCount(count)
    if module in self._modules:
      self._modules[module].SetContainerCount(count)

  def UpdateModuleThreadState(self,
                              module: str,
                              status: Status,
                              thread: str,
                              container: str) -> None:
    """Update the state of a thread within a threaded module for display."""
    if module in self._preflights:
      self._preflights[module].SetThreadState(status, thread, container)
    if module in self._modules:
      self._modules[module].SetThreadState(status, thread, container)

    self.Draw()

  def Draw(self) -> None:
    """Draws the window."""
    if not self.stdscr:
      return

    with self._lock:
      self.stdscr.clear()
      y, _ = self.stdscr.getmaxyx()

      curr_line = 1
      self.stdscr.addstr(curr_line, 0, f' {self._recipe_name}')
      curr_line += 1

      # Preflights
      if self._preflights:
        self.stdscr.addstr(curr_line, 0, '   Preflights:')
        curr_line += 1
        for _, module in self._preflights.items():
          for line in module.Stringify():
            self.stdscr.addstr(curr_line, 0, line)
            curr_line += 1

      # Modules
      self.stdscr.addstr(curr_line, 0, '   Modules:')
      curr_line += 1
      for status in Status:  # Print the modules in Status order
        for _, module in self._modules.items():
          if module.status != status:
            continue
          for line in module.Stringify():
            self.stdscr.addstr(curr_line, 0, line)
            curr_line += 1

      # Messages
      curr_line += 1
      self.stdscr.addstr(curr_line, 0, ' Messages:')
      curr_line += 1

      message_space = y - 4 - curr_line
      start = len(self._messages) - message_space
      start = 0 if start < 0 else start

      for m in self._messages[start::]:
        self.stdscr.addstr(
            curr_line, 0, f'  {m.Stringify(self._messages_longest_source_len)}')
        curr_line += 1
        if curr_line > y - 4:
          break

      # Exceptions
      if self._exception:
        self.stdscr.addstr(y - 2, 0,
            f' Exception encountered: {self._exception.__str__()}')

      self.stdscr.move(curr_line, 0)
      self.stdscr.refresh()

  def PrintMessages(self) -> None:
    """Dump all messages to stdout. Intended to be used when exiting, after
    calling EndCurses()."""

    if self._messages:
      print('Messages')
      for m in self._messages:
        print(f'  {m.Stringify(self._messages_longest_source_len)}')

    if self._exception:
      print('\nException encountered during execution:')
      traceback.print_exception(None,
                                self._exception,
                                self._exception.__traceback__)

    print('')

  def Pause(self) -> None:
    """Ask the user to press any key to continue."""
    with self._lock:
      y, _ = self.stdscr.getmaxyx()

      self.stdscr.addstr(y - 1, 0, "Press any key to continue")
      self.stdscr.getkey()
      self.stdscr.addstr(y - 1, 0, "                         ")
