# -*- coding: utf-8 -*-
"""Processes a directory of artifacts with Turbinia."""

from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import print_function

import os

from turbinia import evidence
from turbinia import TurbiniaException

from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.processors.turbinia_gcp import TurbiniaProcessorBase
from dftimewolf.lib import utils

# pylint: disable=no-member

class TurbiniaArtifactProcessor(TurbiniaProcessorBase):
  """Processes Google Cloud (GCP) disks with Turbinia.

  Attributes:
    directory_path (str): Name of the directory to process.
  """

  def __init__(self, state, critical=False):
    """Initializes a Turbinia Google Cloud (GCP) disks processor.

    Args:
      state (DFTimewolfState): recipe state.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(TurbiniaArtifactProcessor, self).__init__(state, critical=critical)
    self.directory_path = None

  # pylint: disable=arguments-differ
  def SetUp(
      self, directory_path, project, turbinia_zone, sketch_id, run_all_jobs):
    """Sets up the object attributes.

    Args:
      directory_path (str): Name of the directory to process.
      project (str): Name of the GCP project containing the disk to process.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      sketch_id (int): The Timesketch sketch id
      run_all_jobs (bool): Whether to run all jobs instead of a faster subset.
    """
    self.directory_path = directory_path

    try:
      self.TurbiniaSetUp(project, turbinia_zone, sketch_id, run_all_jobs)
    except TurbiniaException as exception:
      self.state.AddError(exception, critical=True)
      return

  def Process(self):
    """Process files with Turbinia."""
    log_file_path = os.path.join(self._output_path, 'turbinia.log')
    print('Turbinia log file: {0:s}'.format(log_file_path))

    if self.state.input and not self.directory_path:
      _, directory_path = self.state.input[0]
      self.directory_path = directory_path
      print(
          'Using directory_path {0:s} from previous collector'.format(
              self.directory_path))

    if os.path.isdir(self.directory_path):
      try:
        self.directory_path = utils.Compress(self.directory_path)
      except RuntimeError as exception:
        self.state.AddError(exception, critical=True)
        return

    evidence_ = evidence.CompressedDirectory(
        compressed_directory=self.directory_path)

    self.TurbiniaProcess(evidence_)


modules_manager.ModulesManager.RegisterModule(TurbiniaArtifactProcessor)
