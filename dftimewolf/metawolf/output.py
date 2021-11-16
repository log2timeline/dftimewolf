#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Metawolf output utilities."""
import hashlib
import subprocess
import time
from datetime import datetime
from datetime import timezone
from typing import Any, List, Optional, Dict

import psutil

from dftimewolf.metawolf import utils

PURPLE = '\033[95m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
ENDC = '\033[0m'

DFTIMEWOLF = 'dftimewolf'
CRITICAL_ERROR = '] CRITICAL'


class MetawolfOutput:
  """MetawolfOutput handles formatting of strings to display in Metawolf."""

  def Welcome(self) -> str:
    """Print Metawolf welcome message.

    Returns:
      str: The welcome message.
    """
    # pylint: disable=anomalous-backslash-in-string
    return self.Color('''
     _____            __           __      __        .__    _____ 
    /     \    ____ _/  |_ _____  /  \    /  \ ____  |  | _/ ____\\
   /  \ /  \ _/ __ \\\\   __\\\\__  \ \   \/\/   //  _ \ |  | \   __\ 
  /    Y    \\\\  ___/ |  |   / __ \_\        /(  <_> )|  |__|  |   
  \____|__  / \___  >|__|  (____  / \__/\  /  \____/ |____/|__|   
          \/      \/            \/       \/                      
      ''', PURPLE)
    # pylint: enable=anomalous-backslash-in-string

  @staticmethod
  def Color(value: Any, color: str) -> str:
    """Return a colored output for stdout.

    Args:
      value (str): The value to format.
      color (str): The color to format the string with.

    Returns:
      str: The formatted string.
    """
    return '{0:s}{1!s}{2:s}'.format(color, value, ENDC)


class MetawolfProcess:
  """MetawolfProcess captures all information about metawolf processes.

  Attributes:
    metawolf_utils (MetawolfUtils): Metawolf utilities.
    process (Any): A subprocess.Popen or psutil.Process object, representing
        metawolf's process.
    session_id (str): The session ID this process belongs to.
    recipe (str): The DFTimewolf recipe this process is executing.
    cmd (List[str]): The command to execute, as a list.
    cmd_readable (str): The command to execute, as a string.
    output_id (int): The output ID used to check the process' output.
    cmd_id (str): The id corresponding to the command being executed.
    outfile_path (str): The path to the file that contains this process' stdout
        and stderr.
    timestamp_readable (str): The timestamp at which this process was run.
    interrupted (bool): True if this process was killed manually, False
        otherwise.
  """

  def __init__(
      self,
      session_id: Optional[str] = None,
      cmd: Optional[List[str]] = None,
      output_id: Optional[int] = None,
      from_dict: Optional[Dict[str, str]] = None,
      metawolf_utils: Optional[utils.MetawolfUtils] = None
  ) -> None:
    """Initialize MetawolfProcess.

    Args:
      session_id (str): Optional. The session ID this process belongs to.
      cmd (List[str]): Optional. The command this process is running. This
          should be of the form [dftimewolf, recipe_name, recipe_arguments...].
      output_id (int): Optional. The output ID that this process corresponds to.
      from_dict (Dict[str, str]): Optional. A json-like dictionary that
          contains the attributes of this object.
      metawolf_utils (MetawolfUtils): Optional. Metawolf utilities. If not
          provided, a default utility object is created.

    Raises:
      ValueError: If the cmd does not match a valid dftimewolf invocation.
    """
    # pylint: disable=line-too-long
    self.metawolf_utils = metawolf_utils if metawolf_utils else utils.MetawolfUtils()
    # pylint: enable=line-too-long
    process = None
    self.status = None
    recipe = ''
    if cmd and cmd[1] in self.metawolf_utils.GetRecipes():
      recipe = cmd[1]

    if not from_dict:
      from_dict = {}
      if cmd and len(cmd) < 2:
        raise ValueError('Command mis-configured. Format: [dftimewolf, '
                         'recipe_name, recipe_arguments...]')

      if cmd and not cmd[0] == DFTIMEWOLF or not recipe:
        raise ValueError('Command mis-configured. Format: [dftimewolf, '
                         'recipe_name, recipe_arguments...]')
    else:
      # Restore last known process state from dict.
      self.status = from_dict['status']
      # Look for background processes if some are still running
      for proc in psutil.process_iter():
        try:
          proc_cmd = proc.cmdline()[1:]  # We discard the parent process
          proc_cmd[0] = proc_cmd[0].split('/')[-1]  # And the full path
          if proc_cmd == from_dict['cmd_readable'].split(' '):
            process = proc
            break
        except (psutil.AccessDenied, psutil.ZombieProcess, IndexError):
          pass

    self.process = process
    self.session_id = from_dict.get('session_id', session_id)
    self.recipe = from_dict.get('recipe', recipe)
    cmd_readable = from_dict.get('cmd_readable')
    if cmd_readable:
      cmd = cmd_readable.split(' ')
    self.cmd = cmd
    if self.cmd:  # Always true here, but needed by Mypy.
      self.cmd_readable = cmd_readable or ' '.join(self.cmd)
    self.output_id = utils.CastToType(
        from_dict.get('output_id', str(output_id)), int)

    self.cmd_id = from_dict.get('cmd_id')
    self.outfile_path = from_dict.get('outfile_path')
    self.timestamp_readable = from_dict.get('timestamp')
    self.interrupted = from_dict.get('interrupted', False)

    self.stdout = None  # type: Any

  def Run(self) -> None:
    """Run the process."""
    # datetime.fromtimestamp format is 2021-09-10 13:46:23.071456+00:00,
    # so we cut the part after '.'
    self.timestamp_readable = str(
      datetime.fromtimestamp(time.time(), timezone.utc)).split(
        '.', maxsplit=1)[0]
    # Metawolf writes each dftimewolf run into a file located in /tmp that
    # is identified by the process's session id, recipe and timestamp.
    file_id = '{0:s}-{1:s}-{2!s}'.format(
        self.session_id, self.recipe, self.timestamp_readable).encode('utf-8')
    self.cmd_id = str(hashlib.sha256(file_id).hexdigest()[:6])
    self.outfile_path = '/tmp/metawolf-{0:s}.log'.format(self.cmd_id)
    self.stdout = open(self.outfile_path, mode='w+')
    if self.cmd:  # Always true here, but needed by Mypy.
      self.process = subprocess.Popen(self.cmd,
                                      shell=False,
                                      stdout=self.stdout,
                                      stderr=self.stdout,
                                      text=True)

  def Poll(self) -> Optional[int]:
    """Poll the process.

    If self.process is a subprocess.Popen object, we call poll(). If
    self.process is a psutil.Process object, we call status().

    If None is returned, the process is still running.
    If 1 is returned, the process failed.
    if 0 is returned, the process exited normally.
    If -1 is returned, the process was not found (status = UNKNOWN).

    Returns:
      int: The process status.
    """

    if not self.process:
      # Process is not in memory anymore.
      return -1

    # https://docs.python.org/3/library/subprocess.html#subprocess.Popen.returncode
    if hasattr(self.process, 'poll'):
      # self.process is a subprocess.Popen object
      err = self.process.poll()
      if err is None:
        return None
      if err > 0:
        return 1
      return 0

    # self.process is a psutil.Process object
    try:
      status = self.process.status()
    except psutil.NoSuchProcess:
      # Process no longer exists
      return -1
    if status == psutil.STATUS_RUNNING:
      return None
    if status == psutil.STATUS_DEAD:
      return 1
    return 0

  def Status(self) -> str:
    """Return the process status.

    Returns:
      str: The status of the running recipe.
    """

    return_code = self.Poll()

    if return_code is None:
      self.status = MetawolfOutput.Color('Running', YELLOW)
      return self.status

    # Process can be in 4 states: interrupted, failed, completed, or unknown.
    if self.interrupted:
      self.status = MetawolfOutput.Color('Interrupted', RED)
      return self.status

    if return_code == -1:
      if not self.status:
        # No previous known state from file.
        self.status = MetawolfOutput.Color('Unknown', BLUE)
      return self.status

    # Else, dftimewolf completed and we need to look into the output file to
    # check whether or not the recipe executed successfully.

    if CRITICAL_ERROR in self.Read(show_warning=False) or return_code == 1:
      self.status = MetawolfOutput.Color('Failed', RED)
      return self.status

    self.status = MetawolfOutput.Color('Completed', GREEN)
    return self.status

  def Read(self, show_warning: bool = True) -> str:
    """Read the output of the process.

    Args:
    show_warning (bool): Optional. Whether or not to print a warning if the file
        we're trying to read was not found.

    Returns:
      str: The stdout of the process written to file.
    """
    if self.outfile_path:
      try:
        with open(self.outfile_path, 'r') as f:
          return f.read()
      except FileNotFoundError:
        if show_warning:
          print(MetawolfOutput.Color(
              'Output file {0:s} does not exist anymore. To clear old output '
              'files, type `clean`'.format(self.outfile_path), RED))
    return ''

  def Terminate(self) -> str:
    """Terminate a process and close its IO file.

    Returns:
      str: An output (e.g. informational message), if any.
    """
    out = ''
    if self.Poll() is None and self.process:
      self.process.terminate()
      out = MetawolfOutput.Color(
          'Killed: {0:s}'.format(self.cmd_id), YELLOW)
      self.interrupted = True
    else:
      out = '{0:s} has already terminated'.format(self.cmd_id)
    if self.stdout:
      # This is always set if the process was not recovered from a previous
      # session
      try:
        self.stdout.close()
      except IOError:
        pass
    return out

  def Marshal(self) -> Dict[str, Any]:
    """Marshal part of the object into a JSON dictionary."""
    return {
        'session_id': self.session_id,
        'recipe': self.recipe,
        'cmd_readable': self.cmd_readable,
        'output_id': self.output_id,
        'cmd_id': self.cmd_id,
        'outfile_path': self.outfile_path,
        'timestamp': self.timestamp_readable,
        'interrupted': self.interrupted,
        'status': self.Status(),
    }
