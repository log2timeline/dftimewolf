# -*- coding: utf-8 -*-
"""Processes cloud artifacts using a remote Turbinia instance."""
from __future__ import unicode_literals

import os
import tempfile
import uuid

from dftimewolf.lib.module import BaseModule

from turbinia import client
from turbinia import config
from turbinia import evidence
from turbinia.pubsub import TurbiniaRequest
from turbinia import TurbiniaException
from turbinia import output_manager


class TurbiniaProcessor(BaseModule):
  """Process cloud disks with remote Turbinia instance.

  Attributes:
    disk_name: Name of the disk to process
    project: The project containing the disk to process
    zone: The zone containing the disk to process
    _gcs_client: The GCS client object
    _output_path: The path to output files
  """

  def __init__(self, state):
    """Initialize the Turbinia artifact processor object.

    Args:
      verbose: Boolean indicating if to use verbose output
    """
    super(TurbiniaProcessor, self).__init__(state)
    self.disk_name = None
    self.project = None
    self.zone = None
    self._output_path = None
    self._gcs_client = None

  def setup(self, disk_name, project, zone):
    """Sets up the object attributes.

    Args:
      disk_name: Name of the disk to process
      project: The project containing the disk to process
      zone: The zone containing the disk to process
    """
    if disk_name is None or project is None or zone is None:
      self.state.add_error(
          'disk_name, project or zone are not all specified in the recipe, '
          'bailing out', critical=True)
    self.disk_name = disk_name
    self.project = project
    self.zone = zone
    self._output_path = tempfile.mkdtemp()

  def cleanup(self):
    pass

  def process(self):
    """Process files with Turbinia."""
    log_file_path = os.path.join(self.output_path, 'turbinia.log')
    self.console_out.VerboseOut('Log file: {0:s}'.format(log_file_path))

    evidence_ = evidence.GoogleCloudDisk(
        disk_name=self.disk_name, project=self.project, zone=self.zone)
    request = TurbiniaRequest()
    request.evidence.append(evidence_)

    try:
      config.LoadConfig()
      region = config.TURBINIA_REGION
      instance = config.PUBSUB_TOPIC
      project = config.PROJECT
      client = TurbiniaClient()

      self.console_out.VerboseOut(
          'Creating Turbinia request {0:s} with Evidence {1:s}'.format(
              request.request_id, evidence_.name))
      client.send_request(request)
      self.console_out.VerboseOut('Waiting for Turbinia request {0:s} to '
                                  'complete'.format(request.request_id))
      client.wait_for_request(
          instance=instance, project=project, region=region,
          request_id=request.request_id, poll_interval=args.poll_interval)
      task_data = client.get_task_data(
          instance=instance, project=project, region=region,
          request_id=request.request_id)
      print client.format_task_status(
          instance=instance, project=project, region=region,
          request_id=request.request_id, all_fields=args.all_fields)
    except TurbiniaException as e:
      self.state.add_error(e, critical=True)


    # This finds all .plaso files in the Turbinia output, and determines if they
    # are local or remote (it's possible this will be running against a local
    # instance of Turbinia).
    local_paths = None
    gs_paths = None
    for task in task_data:
      for path in task.get('saved_paths', []):
        if path.startswith('/') and path.endswith('.plaso'):
          local_paths.append(path)
        if path.startswith('gs://') and path.endswith('.plaso'):
          gs_paths.append(path)

    if not local_paths and not gs_paths:
      self.state.add_error(
          "No .plaso files found in Turbinia output.", critical=True)

    # Any local .plaso files that exist we can add immediately to the output
    [self.state.output.append(p) for p in local_paths if os.path.exists(p)]

    # For files remote in GCS we copy each plaso file back from GCS and then add
    # to output paths
    for path in gs_paths:
      local_path = None
      try:
        output_writer = output_manager.GCSOutputWriter(
            path, local_output_dir=self._output_path)
        local_path = output_writer.copy_from(path)
      except TurbiniaException as e:
        self.state.add_error(e, critical=True)

      if local_path:
        self.state.output.append(local_path)

    if len(self.state.output) == 0:
      self.state.add_error("No .plaso files could be found.", critical=True)
