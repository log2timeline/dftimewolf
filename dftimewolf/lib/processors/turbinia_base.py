# -*- coding: utf-8 -*-
"""Base class for turbinia interactions."""

import getpass
import os
import random
import tempfile
import time
from typing import Dict, List, Optional, Tuple, Any, Union

from turbinia import TurbiniaException
from turbinia import client as turbinia_client
from turbinia import config as turbinia_config
from turbinia import evidence, output_manager
from dftimewolf.lib.logging_utils import WolfLogger


# pylint: disable=abstract-method,no-member
class TurbiniaProcessorBase(object):
  """Base class for processing with Turbinia.

  Attributes:
    turbinia_config_file (str): Full path to the Turbinia config file to use.
    client (TurbiniaClient): Turbinia client.
    instance (str): name of the Turbinia instance
    project (str): name of the GCP project containing the disk to process.
    sketch_id (int): The Timesketch sketch id
    turbinia_recipe (str): Turbinia recipe name.
    turbinia_region (str): GCP region in which the Turbinia server is running.
    turbinia_zone (str): GCP zone in which the Turbinia server is running.
  """

  DEFAULT_YARA_MODULES = 'import "pe"\nimport "math"\nimport "hash"\n\n'

  def __init__(self, logger: WolfLogger) -> None:
    """Initializes a Turbinia base processor.

    Args:
      state (state.DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    self.turbinia_config_file = ''  # type: Any
    self._output_path = str()
    self.client = None  # type: turbinia_client.BaseTurbiniaClient
    self.instance = None
    self.project = str()
    self.sketch_id = int()
    self.turbinia_recipe = str()  # type: Any
    self.turbinia_region = None
    self.turbinia_zone = str()
    self.parallel_count = 5  # Arbitrary, used by ThreadAwareModule
    self.logger = logger

    os.environ['GRPC_POLL_STRATEGY'] = 'poll'

  def _DeterminePaths(
      self,
      task_data: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """Builds lists of local and remote paths from data returned by Turbinia.

    This finds all .plaso, hashes.json, and BinaryExtractorTask files in the
    Turbinia output, and determines if they are local or remote (it's possible
    this will be running against a local instance of Turbinia).

    Args:
      task_data (list[dict]): List of dictionaries representing Turbinia task
          data.

    Returns:
      tuple[list, list]: A tuple of two lists. The first element contains the
          local paths, the second element contains the remote (GS) paths.
    """
    local_paths = []
    gs_paths = []
    for task in task_data:
      # saved_paths may be set to None
      saved_paths = task.get('saved_paths') or []
      for path in saved_paths:

        if path.endswith('.plaso') or \
            path.endswith('BinaryExtractorTask.tar.gz') or \
            path.endswith('hashes.json'):

          if path.startswith('gs://'):
            gs_paths.append(path)
          else:
            local_paths.append(path)

    return local_paths, gs_paths

  def _DownloadFilesFromGCS(self,
                            timeline_label: str,
                            gs_paths: List[str]) -> List[Tuple[str, str]]:
    """Downloads files stored in Google Cloud Storage to the local filesystem.

    Args:
      timeline_label (str): Label to use to construct the path list.
      gs_paths (List[str]):  gs:// URI to files that need to be downloaded
          from GS.

    Raises:
      TurbiniaException: Upon errors downloading from GCS

    Returns:
      list:
        tuple: containing:
          str: The timeline label for this path.
          str: A local path where GS files have been copied to.
    """
    # TODO: Externalize fetching files from GCS buckets to a different module.

    local_paths = []
    for path in gs_paths:
      local_path = None
      output_writer = output_manager.GCSOutputWriter(
          path, local_output_dir=self._output_path)
      local_path = output_writer.copy_from(path)
      self.logger.success('Downloaded {0:s} to {1:s}'.format(path, local_path))

      if local_path:
        local_paths.append((timeline_label, local_path))

    return local_paths

  def TurbiniaSetUp(self,
                    project: str,
                    turbinia_recipe: Union[str, None],
                    turbinia_zone: str,
                    sketch_id: int) -> None:
    """Sets up the object attributes.

    Raises:
      TurbiniaException: For errors in setting up the Turbinia client.

    Args:
      project (str): name of the GCP project containing the disk to process.
      turbinia_recipe (str): Turbinia recipe name.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      sketch_id (int): The Timesketch sketch ID.
    """
    self.project = project
    self.turbinia_recipe = turbinia_recipe
    self.turbinia_zone = turbinia_zone
    self.sketch_id = sketch_id

    turbinia_config.LoadConfig(config_file=self.turbinia_config_file)
    if not self.project:
      self.project = turbinia_config.TURBINIA_PROJECT
    if not self.turbinia_zone:
      self.turbinia_zone = turbinia_config.TURBINIA_ZONE

    if not self.project or not self.turbinia_zone:
      raise TurbiniaException(
          'project or turbinia_zone are not all specified, bailing out')

    self.turbinia_region = turbinia_config.TURBINIA_REGION
    self.instance = turbinia_config.INSTANCE_ID
    if turbinia_config.TURBINIA_PROJECT != self.project:
      raise TurbiniaException(
          'Specified project {0!s} does not match Turbinia configured '
          'project {1!s}. Use gcp_turbinia_disk_copy_ts recipe to copy the '
          'disk into the same project.'.format(
              self.project, turbinia_config.TURBINIA_PROJECT))
    self._output_path = tempfile.mkdtemp()
    self.client = turbinia_client.get_turbinia_client()

  def TurbiniaProcess(
      self,
      evidence_: evidence.Evidence,
      threat_intel_indicators: Optional[List[Optional[str]]] = None,
      yara_rules: Optional[List[str]] = None,
      wait: Optional[bool] = True
      ) -> Union[None, Tuple[List[Dict[str, str]], Any]]:
    """Creates, sends and waits-on a Turbinia processing request.

    Args:
      evidence_: The evidence to process.
      threat_intel_indicator: list of strings used as regular expressions in
          the Turbinia grepper module.
      yara_rules: List of Yara rule strings to use in the Turbinia Yara module.
      wait: Wait until the Turbinia request is done.

    Returns:
      The Turbinia task data. None if wait is False.
    """
    evidence_.validate()
    process_client = turbinia_client.get_turbinia_client()  # issues/600

    recipe = None
    jobs_denylist = None
    yara_text = None

    jobs_denylist = [
        'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob', 'PhotorecJob'
    ]

    if yara_rules:
      yara_text = self.DEFAULT_YARA_MODULES + '\n'.join(list(yara_rules))

    if self.turbinia_recipe:
      # Use a pre-configured turbinia recipe
      recipe = process_client.create_recipe(
          recipe_name=self.turbinia_recipe,
          sketch_id=self.sketch_id,
          yara_rules=yara_text)
    else:
      # Use default recipe with custom parameters
      recipe = process_client.create_recipe(
          sketch_id=self.sketch_id,
          filter_patterns=threat_intel_indicators,
          jobs_denylist=jobs_denylist,
          yara_rules=yara_text)

      request = process_client.create_request(
          requester=getpass.getuser(), recipe=recipe)
      request.evidence.append(evidence_)
    self.logger.success(
      'Creating Turbinia request {0:s} with Evidence {1!s}'.format(
          request.request_id, evidence_.name))
    process_client.send_request(request)

    self.logger.info(
        'Waiting for Turbinia request {0:s} to complete'.format(
            request.request_id))
    if wait:
      return self.TurbiniaWait(request.request_id)

  def TurbiniaWait(self, request_id: str) -> Tuple[List[Dict[str, str]], Any]:
    """Wait for Turbinia Request to finish.

    Args:
      request_id: Request ID for the Turbinia Job.
    Returns:
      The Turbinia task data.
    """
    request_dict = {
        'instance': self.instance,
        'project': self.project,
        'region': self.turbinia_region,
        'request_id': request_id
    }
    task_data = []  # type: List[Dict[str, str]]
    process_client = turbinia_client.get_turbinia_client()
    # Workaround for rate limiting in turbinia when checking task status
    while True:
      try:
        process_client.wait_for_request(**request_dict)
        task_data = process_client.get_task_data(**request_dict)

        message = process_client.format_task_status(
            full_report=True, **request_dict)
        short_message = process_client.format_task_status(**request_dict)
        self.logger.info(short_message)

        return task_data, message
      except RuntimeError as exception:
        if 'Cloud function [gettasks] call failed' not in str(exception) and \
            'RATE_LIMIT_EXCEEDED' not in str(exception):
          raise exception
        delay = 60 + random.randint(0, 30)
        self.logger.info(
            f'Rate limit for gettasks hit. Pausing {delay} seconds.')
        time.sleep(delay)
