# -*- coding: utf-8 -*-
"""Processes a directory of artifacts with Turbinia."""

from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import print_function

import os

from turbinia import evidence
from turbinia import TurbiniaException

from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.processors.turbinia_gcp import TurbiniaProcessorBase

# pylint: disable=no-member

class TurbiniaArtifactProcessor(TurbiniaProcessorBase):
  """Processes Exported GRR Artifacts with Turbinia.

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
      self, directory_path, sketch_id, run_all_jobs):
    """Sets up the object attributes.

    Args:
      directory_path (str): Name of the directory to process.
      sketch_id (int): The Timesketch sketch id
      run_all_jobs (bool): Whether to run all jobs instead of a faster subset.
    """
    self.directory_path = directory_path

    try:
      self.TurbiniaSetUp(None, None, sketch_id, run_all_jobs)
    except TurbiniaException as exception:
      self.state.AddError(exception, critical=True)
      return

  def Process(self):
    """Process files with Turbinia."""
    log_file_path = os.path.join(self._output_path, 'turbinia.log')
    print('Turbinia log file: {0:s}'.format(log_file_path))

    fspaths = self.state.GetContainers(containers.RemoteFSPath)

    for fspath in fspaths:
      print(
          'Processing remote FS path {0:s} from previous collector'.format(
              fspath.path))
      evidence_ = evidence.CompressedDirectory(
          compressed_directory=fspath.path, local_path=fspath.path)
      self.TurbiniaProcess(evidence_)


modules_manager.ModulesManager.RegisterModule(TurbiniaArtifactProcessor)
