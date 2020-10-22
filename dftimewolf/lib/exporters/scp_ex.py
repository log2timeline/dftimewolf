# -*- coding: utf-8 -*-
"""Send files using SCP."""

import os
import subprocess

from dftimewolf.lib.containers import containers
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
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

  def __init__(self, state, name=None, critical=False):
    super(SCPExporter, self).__init__(state, name=name, critical=critical)
    self._paths = None
    self._user = None
    self._hostname = None
    self._destination = None
    self._id_file = None
    self._upload = None
    self._multiplexing = None

  def SetUp(self, # pylint: disable=arguments-differ
            paths,
            destination,
            user,
            hostname,
            id_file,
            direction,
            multiplexing,
            check_ssh):
    """Sets up the _target_directory attribute.

    Args:
      paths (str): Comma-separated list of files to copy.
      user (str): Username at destination host.
      hostname (str): Hostname of destination.
      destination (str): Path to destination on host.
      id_file (str): Identity file to use.
      direction (str): 'upload' or 'download', depending on which directions
          the files should be SCP'd.
      multiplexing (boolean): Whether the module should attempt to use a
          multiplexed SSH connection.
      check_ssh (boolean): Whether to check for SSH connectivity on module
          setup.
    """
    self._destination = destination
    self._hostname = hostname
    self._id_file = id_file
    if paths:
      self._paths = paths.split(',')
    else:
      self._paths = None
    self._user = user
    self._multiplexing = multiplexing

    if direction not in ['upload', 'download']:
      self.ModuleError(
        'Parameter direction must be one of {upload, download}',
        critical=True)
    self._upload = direction == 'upload'

    if check_ssh and not self._SSHAvailable():
      self.ModuleError(
          'Unable to connect to {0:s}.'.format(self._hostname), critical=True)

  def Process(self):
    """Copies the list of paths to or from the remote host."""
    if not self._paths:
      if self._upload:
        # We're uploading local paths to the remote host.
        fspaths = self.state.GetContainers(containers.File)
      else:
        # We're downloading remote paths to the local host.
        fspaths = self.state.GetContainers(containers.RemoteFSPath)
      self._paths = [fspath.path for fspath in fspaths]

    if not self._paths:
      self.ModuleError('No paths specified to SCP module.', critical=True)

    self._CreateDestinationDirectory(remote=self._upload)

    cmd = ['scp']
    # Set options for SSH multiplexing
    if self._multiplexing:
      cmd.extend([
        '-o', 'ControlMaster=auto',
        '-o', 'ControlPath= ~/.ssh/ctrl-%C',
      ])
    if self._id_file:
      cmd.extend(['-i', self._id_file])
    if self._upload:
      # scp /path1 /path2 user@host:/destination
      cmd.extend(self._paths)
      cmd.extend(self._PrefixRemotePaths([self._destination]))
    else:
      # We can use (faster)
      # scp user@host:"/path1 /path2"
      # or (slower)
      # scp user@host:/path1 user@host:/path2 /destination
      cmd.extend(self._PrefixRemotePaths(self._paths))
      cmd.extend([self._destination])

    self.logger.debug('Executing SCP command: {0:s}'.format(' '.join(cmd)))
    ret = subprocess.call(cmd)
    if ret != 0:
      self.ModuleError(
          'Failed copying {0!s}'.format(self._paths), critical=True)

    for path_ in self._paths:
      file_name = os.path.basename(path_)
      full_path = os.path.join(self._destination, file_name)
      if self._upload:
        self.logger.info('Remote filesystem path {0:s}'.format(full_path))
        fspath = containers.RemoteFSPath(
            path=full_path, hostname=self._hostname)
      else:
        self.logger.info('Local filesystem path {0:s}'.format(full_path))
        fspath = containers.File(name=file_name, path=full_path)

      self.state.StoreContainer(fspath)

  def _PrefixRemotePaths(self, paths, group=True):
    """Prefixes a list of paths with remote SSH access information.

    Args:
      paths (list[str]): List of strings representing paths to prefix.
      group (bool): Whether to group all remote filepaths in a single command.

    Returns:
      list[str]: A list of strings with the prefixed paths.
    """
    prefix = self._GenerateRemotePrefix()
    if group:
      prefixed_paths = ['{0:s}:{1:s}'.format(prefix, ' '.join(paths))]
      return prefixed_paths
    prefixed_paths = ['{0:s}:{1:s}'.format(prefix, path) for path in paths]
    return prefixed_paths

  def _GenerateRemotePrefix(self):
    """Generates the remote prefix for this module's configuration.

    Returns:
      str: the remote prefix e.g. 'user@host'
    """
    user = ''
    if self._user:
      user = '{0:s}@'.format(self._user)
    if self._hostname:
      prefix = '{0:s}{1:s}'.format(user, self._hostname)
    return prefix

  def _CreateDestinationDirectory(self, remote):
    """Creates the file's destination directory.

    Args:
      remote (bool): Whether the destination directory should be created on
          the remote host.
    """
    mkdir_command = ['mkdir', '-p', self._destination]

    if remote:
      cmd = ['ssh', self._GenerateRemotePrefix()]
      cmd.extend(mkdir_command)
      self.logger.info(
        'Creating destination directory {0:s} on host {1:s}'.format(
            self._destination, self._hostname))
    else:
      cmd = mkdir_command

    self.logger.info('Shelling out: {0:s}'.format(' '.join(cmd)))
    ret = subprocess.call(cmd)
    if ret != 0:
      self.ModuleError(
          'Failed creating destination directory, bailing.', critical=True)

  def _SSHAvailable(self):
    """Checks that the SSH authentication succeeds on a given host.

    Returns:
      bool: True if host can be reached, False otherwise.
    """
    if not self._hostname:
      return True
    command = ['ssh', '-q']
    if self._user:
      command.extend(['-l', self._user])
    command.extend([self._hostname, 'true'])
    if self._id_file:
      command.extend(['-i', self._id_file])
    self.logger.debug(
        'Checking SSH connectivity with: {0:s}'.format(' '.join(command)))
    ret = subprocess.call(command)
    return ret == 0

modules_manager.ModulesManager.RegisterModule(SCPExporter)
