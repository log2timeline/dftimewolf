# -*- coding: utf-8 -*-
"""Processes artifacts using a local plaso process."""
import os
import subprocess
import tempfile
import uuid

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.containers import containers


class LocalPlasoProcessor(module.BaseModule):
  """Processes a list of file paths with Plaso (log2timeline).

  input: A list of file paths to process.
  output: The path to the resulting Plaso storage file.
  """

  def __init__(self, state, name=None, critical=False):
    super(LocalPlasoProcessor, self).__init__(
        state, name=name, critical=critical)
    self._timezone = None
    self._output_path = None
    self._plaso_path = None

  def _DeterminePlasoPath(self):
    """Checks if log2timeline is somewhere in the user's PATH."""
    for path in os.environ['PATH'].split(os.pathsep):
      full_path = os.path.join(path, 'log2timeline.py')
      if os.path.isfile(full_path):
        self._plaso_path = full_path
        return True
    return False

  def SetUp(self, timezone=None):  # pylint: disable=arguments-differ
    """Sets up the local time zone with Plaso (log2timeline) should use.

    Args:
      timezone (Optional[str]): name of the local time zone.
    """
    self._timezone = timezone
    self._output_path = tempfile.mkdtemp()
    if not self._DeterminePlasoPath():
      self.ModuleError('log2timeline.py was not found in your PATH. To fix: \n'
                       '  apt install plaso-tools',
                       critical=True)


  def Process(self):
    """Executes log2timeline.py on the module input."""
    for file_container in self.state.GetContainers(containers.File, pop=True):
      description = file_container.name
      path = file_container.path
      log_file_path = os.path.join(self._output_path, 'plaso.log')
      self.logger.info('Log file: {0:s}'.format(log_file_path))

      # Build the plaso command line.
      cmd = [self._plaso_path]
      # Since we might be running alongside another Module, always disable
      # the status view.
      cmd.extend(['-q', '--status_view', 'none'])
      if self._timezone:
        cmd.extend(['-z', self._timezone])

      # Analyze all available partitions.
      cmd.extend(['--partition', 'all'])

      # Setup logging.
      cmd.extend(['--logfile', log_file_path])

      # And now, the crux of the command.
      # Generate a new storage file for each plaso run
      plaso_storage_file_path = os.path.join(
          self._output_path, '{0:s}.plaso'.format(uuid.uuid4().hex))
      cmd.extend([plaso_storage_file_path, path])

      # Run the l2t command
      full_cmd = ' '.join(cmd)
      self.logger.info('Running external command: "{0:s}"'.format(full_cmd))
      try:
        l2t_proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, error = l2t_proc.communicate()
        l2t_status = l2t_proc.wait()
      except OSError as exception:
        self.ModuleError(str(exception), critical=True)

      if l2t_status:
        message = ('The log2timeline command {0:s} failed: {1!s}.'
                   ' Check log file for details.').format(full_cmd, error)
        self.ModuleError(message, critical=True)

      container = containers.File(description, plaso_storage_file_path)
      self.state.StoreContainer(container)


modules_manager.ModulesManager.RegisterModule(LocalPlasoProcessor)
