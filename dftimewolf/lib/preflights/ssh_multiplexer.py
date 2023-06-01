"""Opens an SSH connection to a server using ControlMaster directives."""

import subprocess
import uuid

from typing import Optional, List

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class SSHMultiplexer(module.PreflightModule):
  """Opens an SSH connection.

  Attributes:
    hostname (str): The hostname we want to multiplex connections to.
    user (str): The username to connect as.
    id_file (str): SSH private key to use.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    super(SSHMultiplexer, self).__init__(
        state, name=name, critical=critical)
    self.hostname = str()
    self.user = None # type: Optional[str]
    self.id_file = None  # type: Optional[str]
    self.extra_ssh_options = [] # type: Optional[List[str]]
    self.control_filename = f"~/.ssh/ctrl-dftw-{str(uuid.uuid4())}"

  def SetUp(self,  # pylint: disable=arguments-differ
            hostname: str,
            user: Optional[str],
            id_file: Optional[str],
            extra_ssh_options: Optional[List[str]]) -> None:
    """Sets up the SSH multiplexer module's attributes.

    Args:
      hostname (str): The hostname we want to multiplex connections to.
      user (str): The username to connect as.
      id_file (str): SSH private key to use.
      extra_ssh_options (List[str]): Extra -o options to be passed on to the
          SSH command.
    """
    self.hostname = hostname
    self.user = user
    self.id_file = id_file
    self.extra_ssh_options = extra_ssh_options

  def Process(self) -> None:
    """Open a shared SSH connection."""
    command = ['ssh', '-q']
    if self.user:
      command.extend(['-l', self.user])
    if self.id_file:
      command.extend(['-i', self.id_file])
    command.extend([
       '-o', 'ControlMaster=auto',
       '-o', 'ControlPersist=yes',
       '-o', f'ControlPath={self.control_filename}',
    ])
    if self.extra_ssh_options:
      command.extend(self.extra_ssh_options)
    command.extend([self.hostname, 'true'])  # execute `true` and return
    self.PublishMessage(
        f'Opening shared SSH connection to: {" ".join(command)}')
    ret = subprocess.call(command)
    if ret != 0:
      self.ModuleError(
        'Unable to SSH to host {0:s}.'.format(self.hostname), critical=True)
    self.state.AddToCache('ssh_control', self.control_filename)

  def CleanUp(self) -> None:
    """Close the shared SSH connection."""
    command = ['ssh',
               '-O', 'exit',
               '-o', f'ControlPath={self.control_filename}',
               self.hostname]
    ret = subprocess.call(command)
    if ret != 0:
      self.logger.error('Error cleaning up the shared SSH connection. Remove '
                        'any lingering ~/.ssh/ctrl-dftw-* files.')
    else:
      self.logger.info('Successfully cleaned up SSH connection.')



modules_manager.ModulesManager.RegisterModule(SSHMultiplexer)
