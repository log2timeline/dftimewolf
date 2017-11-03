# -*- coding: utf-8 -*-
"""Processes artifacts using a local plaso process."""
from __future__ import unicode_literals

import os
import subprocess
import tempfile
import uuid

from dftimewolf.lib.processors.processors import BaseArtifactProcessor


class LocalPlasoProcessor(BaseArtifactProcessor):
  """Process artifacts with plaso, begetting a new log2timeline.py process.

  Attributes:
    output_path: Where to store the result
    artifacts_path: Source data to process
    plaso_storage_file_name: File name for the resulting Plaso storage file
    plaso_storage_file_path: Full path to the result
    timezone: Timezone to use for Plaso processing
  """

  def __init__(self, artifacts_path, timezone=None, verbose=False):
    """Initialize the Plaso artifact processor object.

    Args:
      artifacts_path: Path to data to process
      timezone: Timezone name (optional)
      verbose: Boolean indicating if to use verbose output
    """
    super(LocalPlasoProcessor, self).__init__(verbose=verbose)
    self.output_path = tempfile.mkdtemp()
    self.artifacts_path = artifacts_path
    self.timezone = timezone
    self.plaso_storage_file_name = '{0:s}.plaso'.format(uuid.uuid4().hex)
    self.plaso_storage_file_path = os.path.join(
        self.output_path, self.plaso_storage_file_name)
    self.results = None

  def process(self):
    """Process files with Log2Timeline from the local plaso install.

    Returns:
      Path to a Plaso storage file

    Raises:
      ValueError: If the local log2timeline.py process fails
    """
    log_file_path = os.path.join(self.output_path, 'plaso.log')
    self.console_out.VerboseOut('Log file: {0:s}'.format(log_file_path))

    cmd = ['log2timeline.py']
    # Since we might be running alongside another Processor, always disable
    # the status view
    cmd.extend(['-q', '--status_view', 'none'])
    if self.timezone:
      cmd.extend(['-z', self.timezone])
    cmd.extend([
        '--logfile', log_file_path, self.plaso_storage_file_path,
        self.artifacts_path
    ])
    self.console_out.VerboseOut(
        'Running external command: {0:s}'.format(' '.join(cmd)))
    # Running the local l2t command
    try:
      l2t_proc = subprocess.Popen(
          cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      _, error = l2t_proc.communicate()
      l2t_status = l2t_proc.wait()
      if l2t_status:
        # self.console_out.StdErr(errors)
        message = 'The command {0:s} failed: {1:s}'.format(' '.join(cmd), error)
        self.errors.append(message)
    except OSError as exception:
      error = 'An error occurred while attempting to run plaso: {0:s}'.format(
          exception)
      self.errors.append(error)
    # Catch all remaining errors since we want to gracefully report them
    except Exception as exception:  #pylint: disable=W0703
      error = 'An unexpected error occured: {0:s}'.format(exception)
      self.errors.append(error)

  @staticmethod
  def launch_processor(collector_output, timezone=None, verbose=False):
    """Thread one or more LocalPlasoProcessor objects.

    Args:
      collector_output: Path to data to process
      timezone: Timezone name (optional)
      verbose: Boolean indicating if to use verbose output

    Returns:
      A list of LocalPlasoProcessor objects that can be join()ed from the
      caller.

    """
    processors = []
    for name, path in collector_output:
      processor = LocalPlasoProcessor(path, timezone, verbose)
      processor.name = name
      processor.start()
      processors.append(processor)

    return processors

  @property
  def output(self):
    """Dynamically generate plugin processor output."""
    return [(self.name, self.plaso_storage_file_path)]


MODCLASS = [('localplaso', LocalPlasoProcessor)]
