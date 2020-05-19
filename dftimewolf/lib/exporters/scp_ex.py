# -*- coding: utf-8 -*-
"""Send files using SCP."""

import subprocess

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class SCPExporter(module.BaseModule):
  """Copies the files in the previous module's output to a given path.

  input: List of paths to copy the files from.
  output: The directory in which the files have been copied.

  Attributes:
    _paths (list[str]): List of files to copy.
    _user (str): Username at destination host.
    _hostname (str): Hostname of destination.
    _destination (str): Path to destination on host.
    _id_file (str): Identity file to use.
  """

  def __init__(self, state):
    super(SCPExporter, self).__init__(state)
    self._paths = None
    self._user = None
    self._hostname = None
    self._destination = None
    self._id_file = None

  def SetUp(self, # pylint: disable=arguments-differ
            paths, destination, user, hostname, id_file, check_ssh):
    """Sets up the _target_directory attribute.

    Args:
      paths (str): Comma-separated list of files to copy.
      user (str): Username at destination host.
      hostname (str): Hostname of destination.
      destination (str): Path to destination on host.
      id_file (str): Identity file to use.
      check_ssh (boolean): Whether to check for SSH connectivity on module
          setup.
    """
    self._destination = destination
    self._hostname = hostname
    self._id_file = id_file
    self._paths = paths.split(",")
    self._user = user

    if check_ssh and not self._SSHAvailable():
      self.state.AddError("Unable to connect to host.", critical=True)

  def Process(self):
    """Copies the list of paths to the destination on user@hostname"""
    dest = self._destination
    user = ""
    if self._user:
      user = "{0:s}@".format(self._user)
    if self._hostname:
      dest = "{0:s}{1:s}:{2:s}".format(user, self._hostname, self._destination)
    cmd = ["scp"]
    cmd.extend(self._paths)
    cmd.append(dest)
    print('Executing SCP command: {0:s}'.format(' '.join(cmd)))
    ret = subprocess.call(cmd)
    if ret != 0:
      self.state.AddError("Failed copying {0!s}".format(self._paths),
                          critical=True)

  def _SSHAvailable(self):
    """Checks that the SSH authentication succeeds on a given host.

    Returns:
      bool: True if host can be reached, False otherwise.
    """
    if not self._hostname:
      return True
    command = ["ssh", "-q"]
    if self._user:
      command.extend(["-l", self._user])
    command.extend([self._hostname, "true"])
    if self._id_file:
      command.extend(["-i", self._id_file])
    print('Checking SSH connectivity with: {0:s}'.format(' '.join(command)))
    ret = subprocess.call(command)
    return ret == 0

modules_manager.ModulesManager.RegisterModule(SCPExporter)
