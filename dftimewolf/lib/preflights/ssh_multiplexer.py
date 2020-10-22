"""Opens an SSH connection to a server using ControlMaster directives."""

import subprocess

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class SSHMultiplexer(module.PreflightModule):
  """Opens an SSH connection.

  Attributes:
    attributes: a list of Attribute proto objects.
  """

  def __init__(self, state, name=None, critical=False):
    super(SSHMultiplexer, self).__init__(
        state, name=name, critical=critical)
    self.hostname = None
    self.user = None
    self.id_file = None

  def SetUp(self, user, hostname, id_file):  # pylint: disable=arguments-differ
    """Sets up the SSH connection.
    """
    self.hostname = hostname
    self.user = user
    self.id_file = id_file

  def Process(self):
    """Open a shared SSH connection."""
    command = ['ssh', '-q']
    if self.user:
      command.extend(['-l', self.user])
    command.extend([self.hostname, 'true'])  # execute `true` and return
    if self.id_file:
      command.extend(['-i', self.id_file])
    command.extend([
       '-o', 'ControlMaster=auto',
       '-o', 'ControlPersist=yes',
       '-o', 'ControlPath= ~/.ssh/ctrl-%C',
    ])
    self.logger.debug(
        'Opening shared SSH connection to: {0:s}'.format(' '.join(command)))
    ret = subprocess.call(command)
    if ret != 0:
      self.ModuleError(
        'Unable to SSH to host {0:s}.'.format(self.hostname), critical=True)

  def CleanUp(self):
    """Close the shared SSH connection."""
    command = ['ssh', '-O', 'exit', self.hostname]
    ret = subprocess.call(command)
    if ret != 0:
      self.logger.error('Error cleaning up the shared SSH connection. Remove '
                        'any lingering ~/.ssh/ctrl-* files.')
    else:
      self.logger.info('Succesfully cleaned up SSH connection.')



modules_manager.ModulesManager.RegisterModule(SSHMultiplexer)
