# -*- coding: utf-8 -*-
"""Curses output management class."""

from enum import Enum
import textwrap
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
  def __init__(self,
               name: str,
               dependencies: List[str],
               runtime_name: Optional[str] = None):
    """Initialize the Module object.

    Args:
      name: The module name of this module.
      dependencies: A list of Runtime names that this module is blocked on.
      runtime_name: The runtime name of this module.
    """
    self.name = name
    self.runtime_name = runtime_name if runtime_name else name
    self.status: Status = Status.PENDING
    self._dependencies: List[str] = dependencies
    self._error_message: str = ''
    self._threads: Dict[str, Dict[str, Any]] = {}
    self._threads_containers_max: int = 0
    self._threads_containers_completed: int = 0

  def Stringify(self) -> List[str]:
    """Returns an CursesDisplayManager friendly string describing the module."""
    module_line = f'     {self.runtime_name}: {self.status.value}'
    thread_lines = []

    if self.status == Status.PENDING and len(self._dependencies) != 0:
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
    """Set the status of the module.

    Args:
      status: The status to set this module to."""
    if self.status not in [Status.ERROR, Status.COMPLETED, Status.CANCELLED]:
      self.status = status

  def SetThreadState(self, thread: str, status: Status, container: str) -> None:
    """Set the state of a thread within a threaded module.

    Args:
      thread: The name of this thread (eg ThreadPoolExecutor-0_5).
      status: The current status of the thread.
      container: The name of the container the thread is currently processing.
    """
    self._threads[thread] = {'status': status,
                             'container': container}
    if status == Status.COMPLETED:
      self._threads_containers_completed += 1

  def SetError(self, message: str) -> None:
    """Sets the error for the module.

    Args:
      message: The error message string."""
    self._error_message = message
    self.status = Status.ERROR

  def SetContainerCount(self, count: int) -> None:
    """Sets the maximum container count for the module.

    Args:
      count: The total number of containers to be processed."""
    self._threads_containers_max = count


class Message:
  """Helper class for managing messages."""

  def __init__(self, source: str, content: str, is_error: bool = False) -> None:
    """Initialize a Message object.

    Args:
      source: The source of the message, eg 'dftimewolf' or a runtime name.
      content: The content of the message.
      is_error: True if the message is an error message, False otherwise."""
    self.source: str = source
    self.content: str = content
    self.is_error: bool = is_error

  def Stringify(self, source_len: int = 0, colorize: bool = False) -> str:
    """Returns an CursesDisplayManager friendly string of the Message.

    Args:
      source_len: The longest source length; used to unify the formatting of
          messages.
      colorize: True if colors should be used."""
    pad = (len(self.source) if len(self.source) > source_len
        else source_len)

    color_code = '\u001b[31;1m' if self.is_error and colorize else ''
    reset_code = '\u001b[0m' if self.is_error and colorize else ''

    return f'[ {self.source:{pad}} ] {color_code}{self.content}{reset_code}'


class CursesDisplayManager:
  """Handles the curses based console output, based on information passed in.
  """

  def __init__(self) -> None:
    """Intializes the CursesDisplayManager."""
    self._recipe_name: str = ''
    self._exception: Union[Exception, None] = None
    self._preflights: Dict[str, Module] = {}
    self._modules: Dict[str, Module] = {}
    self._messages: List[Message] = []
    self._messages_longest_source_len: int = 0
    self._lock = threading.Lock()
    self._stdscr: curses.window = None  # type: ignore

  def StartCurses(self) -> None:
    """Start the curses display."""
    self._stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    self._stdscr.keypad(True)

  def EndCurses(self) -> None:
    """Curses finalisation actions."""
    if True in [m.is_error for m in self._messages] or self._exception:
      self.Pause()

    curses.nocbreak()
    self._stdscr.keypad(False)
    curses.echo()
    curses.endwin()

  def SetRecipe(self, recipe: str) -> None:
    """Set the recipe name.

    Args:
      recipe: The recipe name"""
    self._recipe_name = recipe

  def SetException(self, e: Exception) -> None:
    """Set an Exception to be included in the display.

    Args:
      e: The exception object."""
    self._exception = e

  def SetError(self, module: str, message: str) -> None:
    """Sets the error state ane message for a module.

    Args:
      module: The module name generating the error.
      message: The error message content."""
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
    """Enqueue a message to be displayed.

    Args:
      source: The source of the message, eg 'dftimewolf' or a runtime name.
      content: The message content.
      is_error: True if the message is an error message, False otherwise."""
    if self._messages_longest_source_len < len(source):
      self._messages_longest_source_len = len(source)

    _, x = self._stdscr.getmaxyx()

    content = '\n'.join(
        textwrap.wrap(
            content,
            x - self._messages_longest_source_len - 8,
            subsequent_indent='  ',
            replace_whitespace=False))

    for line in content.split('\n'):
      if line:
        self._messages.append(Message(source, line, is_error))

    self.Draw()

  def EnqueuePreflight(self,
                       name: str,
                       dependencies: List[str],
                       runtime_name: Optional[str]) -> None:
    """Enqueue a preflight module object for display.

    Args:
      name: The name of the preflight module.
      dependencies: runtime names of blocking modules.
      runtime_name: the runtime name of the preflight module."""
    m = Module(name, dependencies, runtime_name)
    self._preflights[m.runtime_name] = m

  def EnqueueModule(self,
                       name: str,
                       dependencies: List[str],
                       runtime_name: Optional[str]) -> None:
    """Enqueue a module object for display.

    Args:
      name: The name of the module.
      dependencies: runtime names of blocking modules.
      runtime_name: the runtime name of the module."""
    m = Module(name, dependencies, runtime_name)
    self._modules[m.runtime_name] = m

  def UpdateModuleStatus(self, module: str, status: Status) -> None:
    """Update the status of a module for display.

    Args:
      module: The runtime name of the module.
      status: the status of the module."""
    if module in self._preflights:
      self._preflights[module].SetStatus(status)
    if module in self._modules:
      self._modules[module].SetStatus(status)

    self.Draw()

  def SetThreadedModuleContainerCount(self, module: str, count: int) -> None:
    """Set the container count that a threaded module will operate on.

    Args:
      module: The runtime name of the threaded module.
      count: The total number of containers the module will process."""
    if module in self._preflights:
      self._preflights[module].SetContainerCount(count)
    if module in self._modules:
      self._modules[module].SetContainerCount(count)

  def UpdateModuleThreadState(self,
                              module: str,
                              status: Status,
                              thread: str,
                              container: str) -> None:
    """Update the state of a thread within a threaded module for display.

    Args:
      module: The runtime name of the module.
      status: The status of the thread.
      thread: The name of the thread, eg 'ThreadPoolExecutor-0_0'.
      container: The name of the container being processed."""
    if module in self._preflights:
      self._preflights[module].SetThreadState(thread, status, container)
    if module in self._modules:
      self._modules[module].SetThreadState(thread, status, container)

    self.Draw()

  def Draw(self) -> None:
    """Draws the window."""
    if not self._stdscr:
      return

    with self._lock:
      self._stdscr.clear()
      y, _ = self._stdscr.getmaxyx()

      curr_line = 1
      self._stdscr.addstr(curr_line, 0, f' {self._recipe_name}')
      curr_line += 1

      # Preflights
      if self._preflights:
        self._stdscr.addstr(curr_line, 0, '   Preflights:')
        curr_line += 1
        for _, module in self._preflights.items():
          for line in module.Stringify():
            self._stdscr.addstr(curr_line, 0, line)
            curr_line += 1

      # Modules
      self._stdscr.addstr(curr_line, 0, '   Modules:')
      curr_line += 1
      for status in Status:  # Print the modules in Status order
        for _, module in self._modules.items():
          if module.status != status:
            continue
          for line in module.Stringify():
            self._stdscr.addstr(curr_line, 0, line)
            curr_line += 1

      # Messages
      curr_line += 1
      self._stdscr.addstr(curr_line, 0, ' Messages:')
      curr_line += 1

      message_space = y - 4 - curr_line
      start = len(self._messages) - message_space
      start = 0 if start < 0 else start

      # Slice the aray, we may not be able to fit all messages on the screen
      for m in self._messages[start:]:
        self._stdscr.addstr(
            curr_line, 0, f'  {m.Stringify(self._messages_longest_source_len)}')
        curr_line += 1

      # Exceptions
      if self._exception:
        self._stdscr.addstr(y - 2, 0,
            f' Exception encountered: {self._exception.__str__()}')

      self._stdscr.move(curr_line, 0)
      self._stdscr.refresh()

  def PrintMessages(self) -> None:
    """Dump all messages to stdout. Intended to be used when exiting, after
    calling EndCurses()."""

    if self._messages:
      print('Messages')
      for m in self._messages:
        print(f'  {m.Stringify(self._messages_longest_source_len, True)}')

    if self._exception:
      print('\nException encountered during execution:')
      print(''.join(traceback.format_exception(None,
                                self._exception,
                                self._exception.__traceback__)))

  def Pause(self) -> None:
    """Ask the user to press any key to continue."""
    with self._lock:
      y, _ = self._stdscr.getmaxyx()

      self._stdscr.addstr(y - 1, 0, "Press any key to continue")
      self._stdscr.getkey()
      self._stdscr.addstr(y - 1, 0, "                         ")
