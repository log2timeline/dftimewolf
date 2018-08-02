# -*- coding: utf-8 -*-
"""Processes cloud artifacts using a remote Turbinia instance."""
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import print_function

import os
import tempfile

from dftimewolf.lib.module import BaseModule

from turbinia import client as turbinia_client
from turbinia import config
from turbinia import evidence
from turbinia import output_manager
from turbinia import TurbiniaException
from turbinia.message import TurbiniaRequest


class TurbiniaProcessor(BaseModule):
  """Process cloud disks with a remote Turbinia instance.

  Attributes:
    client: A TurbiniaClient object
    disk_name: Name of the disk to process
    instance (string): The name of the Turbinia instance
    project: The project containing the disk to process
    region (string): The region Turbinia is in
    zone: The zone containing the disk to process
    _output_path: The path to output files
  """

  def __init__(self, state):
    """Initialize the Turbinia artifact processor object.

    Args:
      state: The dfTimewolf state object
    """
    super(TurbiniaProcessor, self).__init__(state)
    self.client = None
    self.disk_name = None
    self.instance = None
    self.project = None
    self.region = None
    self.zone = None
    self._output_path = None

  def setup(self, disk_name, project, zone):  # pylint: disable=arguments-differ
    """Sets up the object attributes.

    Args:
      disk_name: Name of the disk to process
      project: The project containing the disk to process
      zone: The zone containing the disk to process
    """
    # TODO: Consider the case when multiple disks are provided by the previous
    # module or by the CLI.
    if self.state.input and not disk_name:
      _, disk = self.state.input[0]
      disk_name = disk.name
      print('Using disk {0:s} from previous collector'.format(disk_name))

    if disk_name is None or project is None or zone is None:
      self.state.add_error(
          'disk_name, project or zone are not all specified, bailing out',
          critical=True)
      return
    self.disk_name = disk_name
    self.project = project
    self.zone = zone
    self._output_path = tempfile.mkdtemp()

    try:
      config.LoadConfig()
      self.region = config.TURBINIA_REGION
      self.instance = config.PUBSUB_TOPIC
      if config.PROJECT != self.project:
        self.state.add_error(
            'Specified project {0:s} does not match Turbinia configured '
            'project {1:s}. Use gcp_forensics_import recipe to copy the disk '
            'into the same project.'.format(
                self.project, config.PROJECT), critical=True)
        return
      self.client = turbinia_client.TurbiniaClient()
    except TurbiniaException as e:
      self.state.add_error(e, critical=True)
      return

  def cleanup(self):
    pass

  def process(self):
    """Process files with Turbinia."""
    log_file_path = os.path.join(self._output_path, 'turbinia.log')
    print('Turbinia log file: {0:s}'.format(log_file_path))

    evidence_ = evidence.GoogleCloudDisk(
        disk_name=self.disk_name, project=self.project, zone=self.zone)
    request = TurbiniaRequest()
    request.evidence.append(evidence_)

    try:
      print('Creating Turbinia request {0:s} with Evidence {1:s}'.format(
          request.request_id, evidence_.name))
      self.client.send_request(request)
      print('Waiting for Turbinia request {0:s} to complete'.format(
          request.request_id))
      self.client.wait_for_request(
          instance=self.instance, project=self.project, region=self.region,
          request_id=request.request_id)
      task_data = self.client.get_task_data(
          instance=self.instance, project=self.project, region=self.region,
          request_id=request.request_id)
      print(self.client.format_task_status(
          instance=self.instance, project=self.project, region=self.region,
          request_id=request.request_id, all_fields=True))
    except TurbiniaException as e:
      self.state.add_error(e, critical=True)
      return

    # This finds all .plaso files in the Turbinia output, and determines if they
    # are local or remote (it's possible this will be running against a local
    # instance of Turbinia).
    local_paths = []
    gs_paths = []
    timeline_label = '{0:s}-{1:s}'.format(self.project, self.disk_name)
    for task in task_data:
      for path in task.get('saved_paths', []):
        if path.startswith('/') and path.endswith('.plaso'):
          local_paths.append(path)
        if path.startswith('gs://') and path.endswith('.plaso'):
          gs_paths.append(path)

    if not local_paths and not gs_paths:
      self.state.add_error(
          'No .plaso files found in Turbinia output.', critical=True)
      return

    # Any local .plaso files that exist we can add immediately to the output
    self.state.output = [
        (timeline_label, p) for p in local_paths if os.path.exists(p)]

    # For files remote in GCS we copy each plaso file back from GCS and then add
    # to output paths
    # TODO: Externalize fetching files from GCS buckets to a different module.
    for path in gs_paths:
      local_path = None
      try:
        output_writer = output_manager.GCSOutputWriter(
            path, local_output_dir=self._output_path)
        local_path = output_writer.copy_from(path)
      except TurbiniaException as e:
        self.state.add_error(e, critical=True)
        return

      if local_path:
        self.state.output.append((timeline_label, local_path))

    if not self.state.output:
      self.state.add_error('No .plaso files could be found.', critical=True)
