# -*- coding: utf-8 -*-
"""Export processing results to Timesketch."""

from __future__ import print_function
from __future__ import unicode_literals

import os
import shutil

from dftimewolf.lib.exporters.exporters import BaseExporter


class LocalFilesystemExporter(BaseExporter):
  """Export results of a collector or processor to the local filesystem.

  Attributes:
    previous_output: (name, path) tuple to export.
    directory: (str) absolute or relative path pointing to a directory into
        which files should be copied.
  """

  def __init__(self, previous_output, directory, verbose=False):
    """Initializes a LocalFilesystemExporter

    Args:
      previous_output: (name, path) tuple to export.
      directory: directory into which files should be copied.
      verbose: Whether verbose output is desired.
    """
    super(LocalFilesystemExporter, self).__init__(verbose=verbose)
    self.previous_output = previous_output
    self.directory = directory
    self.output = []

    if not os.path.exists(directory):
      try:
        os.makedirs(directory)
      except OSError as exception:
        self.console_out.StdErr(
            'An unknown error occurred: {0:s}'.format(exception))
    self.console_out.VerboseOut(
        'Files will be copied to {0:s}'.format(directory))

  def export(self):
    """Does the actual copying of files."""
    for source, path in self.previous_output:
      self._copy_file_or_directory(path, self.directory)
      self.console_out.StdOut(
          '({0:s}) {1:s} -> {2:s}'.format(source, path, self.directory))

  def _copy_file_or_directory(self, source, destination_directory):
    """Recursively copies files from source to destination_directory.

    Args:
        source: source file or directory to copy into destination_directory
        destination_directory: destination directory in which to copy source
    """
    for item in os.listdir(source):
      full_source = os.path.join(source, item)
      full_destination = os.path.join(destination_directory, item)
      if os.path.isdir(full_source):
        shutil.copytree(full_source, full_destination)
      else:
        shutil.copy2(full_source, full_destination)

  @staticmethod
  def launch_exporter(processor_output, directory):
    """Threads one or more LocalFilesystemExporter objects.

    Args:
      processor_output: List of (name, path) tuples to export.
      directory: destination directory of copy.

    Returns:
      A list consisting of a single LocalFilesystemExporter object that can be
          join()ed from the caller.
    """
    exporter = LocalFilesystemExporter(processor_output, directory)
    exporter.start()
    return [exporter]

MODCLASS = [('timesketch', LocalFilesystemExporter)]
