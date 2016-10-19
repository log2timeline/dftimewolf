"""Timewolf artifact processors, responsible for processing artifacts."""

import argparse
import os
import tempfile
import uuid

from plaso.cli import tools as cli_tools
from tools import log2timeline

from dftimewolf.lib import utils


class BaseArtifactProcessor(object):
  """Base class for artifact processors."""

  def __init__(self, verbose):
    super(BaseArtifactProcessor, self).__init__()
    self.console_out = utils.TimewolfConsoleOutput(
        sender=self.__class__.__name__, verbose=verbose)

  def Process(self):
    """Process artifacts."""
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
      artifacts_path: Local path for plaso artifact input
      timezone: Timezone name
      verbose: Boolean indicating if verbose output is desired
    """
    super(PlasoArtifactProcessor, self).__init__(verbose=verbose)
    self.output_path = tempfile.mkdtemp()
    self.artifacts_path = artifacts_path
    self.timezone = timezone
    self.plaso_storage_file_name = u'{0:s}.plaso'.format(uuid.uuid4().hex)
    self.plaso_storage_file_path = os.path.join(self.output_path,
                                                self.plaso_storage_file_name)

  def Process(self):
    """Process files with Log2Timeline from Plaso."""
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
    return self.plaso_storage_file_path


def ProcessArtifactsHelper(collected_artifacts, timezone, verbose):
  """Helper function to process data with Plaso.

  Args:
    collected_artifacts: List of tuples with path to data to process and a name
                         to use as timeline name
    timezone: Timezone name
    verbose: Boolean indicating if verbose output is to be used

  Returns:
    List of tuples with path to Plaso storage file and name of the timeline
  """
  processed_artifacts = []
  for path, name in collected_artifacts:
    if os.path.exists(path):
      plaso_processor = PlasoArtifactProcessor(path, timezone, verbose=verbose)
      plaso_storage_file = plaso_processor.Process()
      processed_artifacts.append((plaso_storage_file, name))
  return processed_artifacts
