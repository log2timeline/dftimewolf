# -*- coding: utf-8 -*-
"""Timewolf artifact processors, responsible for processing artifacts."""

import argparse
import os
import subprocess
import sys
import tempfile
import threading
import uuid

from plaso.cli import tools as cli_tools
from tools import log2timeline

from dftimewolf.lib import utils


class BaseArtifactProcessor(threading.Thread):
  """Base class for artifact processors."""

  def __init__(self, verbose):
    super(BaseArtifactProcessor, self).__init__()
    self.console_out = utils.TimewolfConsoleOutput(
        sender=self.__class__.__name__, verbose=verbose)

  def Process(self):
    """Process artifacts.

    Returns:
      str: path to a file containing results of processing.
    """
    raise NotImplementedError


class PlasoArtifactProcessor(BaseArtifactProcessor):
  """Process artifacts with Plaso log2timeline tool.

    Attributes:
      output_path: Local path for plaso file output
      artifacts_path: Local path for plaso artifact input
      timezone: Timezone name
      plaso_storage_file_name: Name of output plaso file
      plaso_storage_file_path: output_path + plaso_storage_file_name
  """

  def __init__(self, artifacts_path, timezone=None, verbose=False):
    """Initialize the Plaso artifact processor object.

    Args:
      artifacts_path (str): Local path for plaso artifact input
      timezone (str): Time zone name
      verbose (bool): whether verbose output is desired
    """
    super(PlasoArtifactProcessor, self).__init__(verbose=verbose)
    self.output_path = tempfile.mkdtemp()
    self.artifacts_path = artifacts_path
    self.timezone = timezone
    self.plaso_storage_file_name = u'{0:s}.plaso'.format(uuid.uuid4().hex)
    self.plaso_storage_file_path = os.path.join(self.output_path,
                                                self.plaso_storage_file_name)
    self.results = None

  def run(self):
    """Starts a thread"""
    self.Process()

  def Process(self):
    """Process files with Log2Timeline from Plaso.

    Returns:
      str: path to a Plaso storage file.
    """
    log_file_path = os.path.join(self.output_path, u'plaso.log')
    self.console_out.VerboseOut(u'Log file: {0:s}'.format(log_file_path))

    # Setup Plaso Log2Timeline tool
    output_writer = cli_tools.CLIOutputWriter(encoding=u'utf-8')
    tool = log2timeline.Log2TimelineTool(output_writer=output_writer)

    # Configure Log2Timeline
    options = argparse.Namespace()
    options.hashers = u'all'
    options.dependencies_check = False
    options.serializer_format = u'json'
    options.status_view_mode = u'window'
    options.log_file = log_file_path
    # Let plaso choose the appropriate number of workers
    options.workers = 0
    options.source = self.artifacts_path
    options.output = self.plaso_storage_file_path
    if self.timezone:
      options.timezone = self.timezone
    tool.ParseOptions(options)

    # Run the tool
    tool.ProcessSources()
    self.console_out.VerboseOut(u'Storage file: {0:s}'.format(
        self.plaso_storage_file_path))
    self.results = self.plaso_storage_file_path


class LocalPlasoArtifactProcessor(PlasoArtifactProcessor):
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
    super(LocalPlasoArtifactProcessor, self).__init__(
        artifacts_path, timezone=timezone, verbose=verbose)

  def Process(self):
    """Process files with Log2Timeline from the local plaso install.

    Returns:
      Path to a Plaso storage file

    Raises:
      ValueError: If the local log2timeline.py process fails
    """
    log_file_path = os.path.join(self.output_path, u'plaso.log')
    self.console_out.VerboseOut(u'Log file: {0:s}'.format(log_file_path))

    cmd = [u'log2timeline.py']
    # Since we might be running alongside another Processor, always disable
    # the status view
    cmd.extend([u'-q', u'--status_view', u'none'])
    if self.timezone:
      cmd.extend([u'-z', self.timezone])
    cmd.extend([
        u'--logfile', log_file_path, self.plaso_storage_file_path,
        self.artifacts_path
    ])
    self.console_out.VerboseOut(u'Running external command: {0:s}'.format(
        u' '.join(cmd)))
    # Running the local l2t command
    l2t_proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, errors = l2t_proc.communicate()
    l2t_status = l2t_proc.wait()
    if l2t_status:
      print >> sys.stderr, errors
      raise ValueError(u'The command {0:s} failed'.format(u' '.join(cmd)))


def ProcessArtifactsHelper(collected_artifacts, timezone, local_plaso, verbose):
  """Helper function to process data with Plaso.

  Args:
    collected_artifacts (list[tuple]): tuples with a timeline name and the path
        to the data to processed.
    timezone (str): Timezone name.
    local_plaso: Boolean indicating if to use the current system's plaso
	install.
    verbose (bool): whether verbose output is to be used.

  Returns:
    list(tuple): containing:
      str: path to plaso storage file.
      str: name to use for Timesketch timeline.
  """
  # Build list of artifact processors and start processing in parallel
  artifact_processors = []
  for artifact in collected_artifacts:
    name = artifact[0]
    path = artifact[1]
    if os.path.exists(path):
      if local_plaso:
        plaso_processor = LocalPlasoArtifactProcessor(
            path, timezone, verbose=verbose)
      else:
        plaso_processor = PlasoArtifactProcessor(
            path, timezone, verbose=verbose)
      plaso_processor.start()
      plaso_processor.join()
      artifact_processors.append((plaso_processor, name))

  # Wait for all processors to finish
  for (processor, name) in artifact_processors:
    processor.join()

  processed_artifacts = ((processor.plaso_storage_file_path, name)
                         for (processor, name) in artifact_processors)

  return processed_artifacts
