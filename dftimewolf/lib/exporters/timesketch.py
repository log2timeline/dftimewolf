# -*- coding: utf-8 -*-
"""Export processing results to Timesketch."""

from __future__ import print_function
from __future__ import unicode_literals

import syslog

from dftimewolf.lib import timesketch_utils
from dftimewolf.lib.exporters.exporters import BaseExporter


class TimesketchExporter(BaseExporter):
  """Export processing results to Timesketch.

  Attributes:
    timesketch_api: Timesketch API object
    incident_id: Incident ID or description associated with the investigation
    sketch_id: Timesketch Sketch ID the timeline will be added to
  """

  def __init__(self, timesketch_api, incident_id, sketch_id, verbose, paths):
    """Initializes a filesystem collector.

    Args:
      timesketch_api: Timesketch API object
      incident_id: Incident ID or description associated with the investigation
      sketch_id: If provided, append the timelines to a given sketch
      verbose: Whether verbose output is desired.
      paths: List of (name, path) tuples to export
    """
    super(TimesketchExporter, self).__init__(verbose=verbose)

    self.timesketch_api = timesketch_api
    self.incident_id = incident_id
    self.sketch_id = sketch_id
    self.paths = paths
    self.sketch_url = None
    self.output = None

    if not self.sketch_id:
      if incident_id:
        sketch_name = incident_id
        sketch_description = incident_id
      else:
        sketch_name = 'Untitled sketch'
        sketch_description = 'No description provided'
      self.sketch_id = timesketch_api.create_sketch(
          sketch_name, sketch_description)
      self.console_out.StdOut(
          'New sketch created: {0:d}'.format(self.sketch_id))
      syslog.syslog('New sketch created: {0:d}'.format(self.sketch_id))

  def export(self):
    """Executes a Timesketch export.

    Returns:
      String containing a timesketch URL
    """
    self.output = []
    self.timesketch_api.export_artifacts(self.paths, self.sketch_id)
    self.sketch_url = self.timesketch_api.get_sketch_url(self.sketch_id)
    self.console_out.StdOut(
        'Your Timesketch URL is: {0:s}'.format(self.sketch_url))
    self.output.append(self.sketch_url)
    return self.sketch_url

  @staticmethod
  def launch_exporter(
      ts_endpoint, ts_username, ts_password, incident_id, sketch_id, verbose,
      processor_output):
    """Threads one or more TimesketchExporter objects.

    Args:
      ts_endpoint: URL of destination Timesketch server
      ts_username: Timesketch username
      ts_password: Timesketch password
      incident_id: Incident ID or description associated with the investigation
      sketch_id: If provided, append the timelines to a given sketch
      verbose: Whether verbose output is desired.
      processor_output: List of (name, path) tuples to export

    Returns:
      A list of TimesketchExporter objects that can be join()ed from the caller.
    """

    print('Using timesketch endpoint: {0:s}'.format(ts_endpoint))

    timesketch_api = timesketch_utils.TimesketchApiClient(
        ts_endpoint, ts_username, ts_password)
    exporter = TimesketchExporter(
        timesketch_api, incident_id, sketch_id, verbose, processor_output)
    exporter.start()
    return [exporter]


MODCLASS = [('timesketch', TimesketchExporter)]
