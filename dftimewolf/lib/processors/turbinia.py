
# -*- coding: utf-8 -*-
"""Processes cloud artifacts using a remote Turbinia instance."""
from __future__ import unicode_literals

import os
import tempfile
import uuid

from dftimewolf.lib.processors.processors import BaseArtifactProcessor

from turbinia import config
from turbinia import evidence
from turbinia import task_manager
from turbinia.pubsub import TurbiniaRequest


class TurbiniaProcessor(BaseArtifactProcessor):
  """Process cloud disks with remote Turbinia instance.

  Attributes:
    disk_name: Name of the disk to process
    project: The project containing the disk to process
    zone: The zone containing the disk to process
  """

  def __init__(self, disk_name, project, zone, verbose=False):
    """Initialize the Turbinia artifact processor object.

    Args:
      verbose: Boolean indicating if to use verbose output
    """
    super(TurbiniaProcessor, self).__init__(verbose=verbose)
    self.disk_name = disk_name
    self.project = project
    self.zone = zone

  def process(self):
    """Process files with Turbinia.

    Returns:
      Path to a Plaso storage file

    Raises:
      ValueError: If the Turbinia process fails
    """
    log_file_path = os.path.join(self.output_path, 'turbinia.log')
    self.console_out.VerboseOut('Log file: {0:s}'.format(log_file_path))

    evidence_ = evidence.GoogleCloudDisk(
        disk_name=self.disk_name, project=self.project, zone=self.zone)
    request = TurbiniaRequest()
    request.evidence.append(evidence_)

    self.console_out.VerboseOut(
        'Creating PubSub request {0:s} with evidence {1:s}'.format(
            request.request_id, evidence_.name))

    config.LoadConfig()
    task_manager_ = task_manager.get_task_manager()
    task_manager_.setup()
    task_manager_.server_pubsub.send_request(request)

    self.console_out.VerboseOut('Waiting for Turbinia request {0:s} to '
        'complete'.format(request.request_id))
    region = config.TURBINIA_REGION
    WaitForRequest(
        instance=config.PUBSUB_TOPIC, project=config.PROJECT, region=region,
        request_id=request.request_id, poll_interval=args.poll_interval)
    PrintTaskStatus(
        instance=config.PUBSUB_TOPIC, project=config.PROJECT, region=region,
        request_id=request.request_id, all_fields=args.all_fields)

  @staticmethod
  def launch_processor(collector_output, verbose=False):
    """Thread one or more LocalPlasoProcessor objects.

    Args:
      collector_output: Path to data to process
      verbose: Boolean indicating if to use verbose output

    Returns:
      A list of TurbiniaProcessor objects that can be join()ed from the
      caller.

    """
    processors = []
    # TODO(aarontp): Figure out the correct path
    for name, disk_name in collector_output:
      processor = TurbiniaProcesor(disk_name, project, zone, verbose)
      processor.name = name
      processor.start()
      processors.append(processor)

    return processors

  @property
  def output(self):
    """Dynamically generate plugin processor output."""
    return [(self.name, self.plaso_storage_file_path)]


MODCLASS = [('turbinia', TurbiniaProcessor)]
