# -*- coding: utf-8 -*-
"""Collect artifacts from the local filesystem."""

from __future__ import unicode_literals

import os

from dftimewolf.lib.collectors.collectors import BaseCollector


class FilesystemCollector(BaseCollector):
  """Collect artifacts from the local filesystem.

  Attributes:
    output_path: Path to store collected artifacts.
    name: Name for the collection of collected artifacts.
    output: List of (name, path) tuples to process.
  """

  def __init__(self, path, name=None, verbose=False):
    """Initializes a filesystem collector.

    Args:
      path: path to the files to collect.
      name: name of the collection.
      verbose: whether verbose output is desired.
    """
    super(FilesystemCollector, self).__init__(verbose=verbose)
    self.name = name or os.path.basename(path)
    self.output_path = path
    self.output = None

  def collect(self):
    """Collect the files.

    Returns:
      list: of tuples:
        str: the name provided for the collection.
        str: path to the files for collection.
    """
    self.console_out.VerboseOut('Artifact path: {0:s}'.format(self.output_path))
    return [(self.name, self.output_path)]

  @property
  def collection_name(self):
    """Name for the collection of collected artifacts.

    Returns:
      str: name of the artifact collection
    """
    if not self.name:
      self.name = os.path.basename(self.output_path.rstrip('/'))
    self.console_out.VerboseOut(
        'Artifact collection name: {0:s}'.format(self.name))
    return self.name

  @staticmethod
  def launch_collector(paths, verbose=False):
    """Threads one or more FilesystemCollector objects.

    Iterates over the values of paths and starts a Filesystem Collector
    for each.

    Args:
      paths: List of strings representing paths to collect files from
      verbose: Print extra output to stdout (default: False)

    Returns:
      A list of FilesystemCollector objects that can be join()ed from the
      caller.
    """
    collectors = []
    for path in paths:
      collector = FilesystemCollector(path, verbose=verbose)
      collector.start()
      collectors.append(collector)
    return collectors


MODCLASS = [('filesystem', FilesystemCollector)]
