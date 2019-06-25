# -*- coding: utf-8 -*-
"""Collect artifacts from the local filesystem."""

from __future__ import unicode_literals

import subprocess

from dftimewolf.lib.module import BaseModule

class Scp(BaseModule):
  """Copies the files in the previous module's output to a given path.

  input: List of paths to copy the files from.
  output: The directory in which the files have been copied.
  """

  def __init__(self, state):
    super(Scp, self).__init__(state)
    self._target_directory = None

  def setup(self, paths, destination, user, hostname, id_file):
    """Sets up the _target_directory attribute.

    Args:
      target_directory: Directory in which collected files will be dumped.
      paths: List of files to copy.
      user: Username at destination host.
      hostname: Hostname of destination.
      destination: Path to destination on host.
      id_file: Identity file to use.
    """
    self._paths = paths.split(",")
    self._user = user
    self._hostname = hostname
    self._destination = destination
    self._id_file = id_file

    if not self._ssh_available():
      self.state.add_error("Unable to connect to host.", critical=True)

  def cleanup(self):
    pass

  def process(self):
    """copies the list of paths to the destination on user@hostname"""
    dest = self._destination
    if self._hostname:
      dest = "{0:s}@{1:s}:{2:s}".format(self._user, self._hostname, self._destination)
    cmd = ["scp"]
    cmd.extend(self._paths)
    cmd.append(dest)
    ret = subprocess.call(cmd)
    if ret:
      self.state.add_error("Failed copying {0:s}".format(self._paths), critical=False)

  def _ssh_available(self):
    """returns true if host can be reached, false otherwise"""
    if not self._hostname:
      return True
    command = ["ssh", "-q", "-l", self._user ,self._hostname, "true"]
    if self._id_file:
      command.extend(["-i", self._id_file])
    ret = subprocess.call(command)
    return not ret
