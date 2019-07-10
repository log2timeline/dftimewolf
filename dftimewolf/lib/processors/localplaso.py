# -*- coding: utf-8 -*-
"""Processes artifacts using a local plaso process."""
from __future__ import print_function
from __future__ import unicode_literals

import os
import subprocess
import tempfile
import uuid

from dftimewolf.lib import module


class LocalPlasoProcessor(module.BaseModule):
  """Processes a list of file paths with Plaso (log2timeline).

  input: A list of file paths to process.
  output: The path to the resulting Plaso storage file.
  """

  def __init__(self, state):
    super(LocalPlasoProcessor, self).__init__(state)
    self._timezone = None
    self._output_path = None

  def setup(self, timezone=None):  # pylint: disable=arguments-differ
    """Sets up the _timezone attribute.

    Args:
      timezone: Timezone name (optional)
    """
    self._timezone = timezone
    self._output_path = tempfile.mkdtemp()

  def Process(self):
    """Executes log2timeline.py on the module input."""
    for description, path in self.state.input:
      log_file_path = os.path.join(self._output_path, 'plaso.log')
      print('Log file: {0:s}'.format(log_file_path))

      # Build the plaso command line.
      cmd = ['log2timeline.py']
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
      print('Running external command: "{0:s}"'.format(full_cmd))
      try:
        l2t_proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, error = l2t_proc.communicate()
        l2t_status = l2t_proc.wait()
        if l2t_status:
          # self.console_out.StdErr(errors)
          message = ('The log2timeline command {0:s} failed: {1!s}.'
                     ' Check log file for details.').format(full_cmd, error)
          self.state.add_error(message, critical=True)
        self.state.output.append((description, plaso_storage_file_path))
      except OSError as exception:
        self.state.add_error(str(exception), critical=True)
      # Catch all remaining errors since we want to gracefully report them
      except Exception as exception:  # pylint: disable=broad-except
        self.state.add_error(str(exception), critical=True)
