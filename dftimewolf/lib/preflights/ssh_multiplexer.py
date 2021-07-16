"""Opens an SSH connection to a server using ControlMaster directives."""

import subprocess
from typing import Optional

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
               name: Optional[str],
               critical: bool=False) -> None:
    super(SSHMultiplexer, self).__init__(
        state, name=name, critical=critical)
    self.hostname = str()
    self.user = None # type: Optional[str]
    self.id_file = None  # type: Optional[str]

  def SetUp(self,  # pylint: disable=arguments-differ
            hostname: str,
            user: Optional[str]=None,
            id_file: Optional[str]=None) -> None:
    """Sets up the SSH multiplexer module's attributes.

    Args:
      hostname (str): The hostname we want to multiplex connections to.
      user (str): The username to connect as.
      id_file (str): SSH private key to use.
    """
    self.hostname = hostname
    self.user = user
    self.id_file = id_file

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
       '-o', 'ControlPath=~/.ssh/ctrl-%C',
    ])
    command.extend([self.hostname, 'true'])  # execute `true` and return
    self.logger.debug(
        'Opening shared SSH connection to: {0:s}'.format(' '.join(command)))
    ret = subprocess.call(command)
    if ret != 0:
      self.ModuleError(
        'Unable to SSH to host {0:s}.'.format(self.hostname), critical=True)

  def CleanUp(self) -> None:
    """Close the shared SSH connection."""
    command = ['ssh',
               '-O', 'exit',
               '-o', 'ControlPath=~/.ssh/ctrl-%C',
               self.hostname]
    ret = subprocess.call(command)
    if ret != 0:
      self.logger.error('Error cleaning up the shared SSH connection. Remove '
                        'any lingering ~/.ssh/ctrl-* files.')
    else:
      self.logger.info('Succesfully cleaned up SSH connection.')



modules_manager.ModulesManager.RegisterModule(SSHMultiplexer)
