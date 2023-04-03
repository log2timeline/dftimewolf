# -*- coding: utf-8 -*-
"""Base class for turbinia interactions."""

import getpass
import os
import tarfile
import tempfile
import time
from typing import Dict, List, Optional, Tuple, Any, Union
import collections

import turbinia_api_lib

from dftimewolf.lib.logging_utils import WolfLogger
from dftimewolf.lib import module

from turbinia_api_lib.api import turbinia_requests_api
from turbinia_api_lib.api import turbinia_request_results_api
from turbinia_client.helpers import formatter as turbinia_formatter
from turbinia_client.helpers import auth_helper


class TurbiniaException(Exception):
  pass


# pylint: disable=abstract-method,no-member
class TurbiniaProcessorBaseAPI(module.BaseModule):
  """Base class for processing with Turbinia.

  Attributes:
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
    self._output_path = str()
    self.client = None
    self.instance = None
    self.project = str()
    self.incident_id = int()
    self.sketch_id = int()
    self.turbinia_recipe = str()  # type: Any
    self.turbinia_region = None
    self.turbinia_zone = str()
    self.parallel_count = 5  # Arbitrary, used by ThreadAwareModule
    self.logger = logger
    self._client_config = turbinia_api_lib.Configuration(
        host="http://127.0.0.1:8000")
    os.environ['GRPC_POLL_STRATEGY'] = 'poll'

  def _DeterminePaths(self, task_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """Builds lists of local and remote paths from data returned by Turbinia.

    This finds all .plaso, hashes.json, and BinaryExtractorTask files in the
    Turbinia output, and determines if they are local or remote (it's possible
    this will be running against a local instance of Turbinia).

    Args:
      task_data (list[dict]): List of dictionaries representing Turbinia task
          data.

    Returns:
      Dict[str, List[str]]) A dict containing task identifiers as keys. The
          values are lists of output file paths.
    """
    result = collections.defaultdict(list)
    interesting_suffixes = [
        '.plaso', 'BinaryExtractorTask.tar.gz', 'hashes.json',
        'fraken_stdout.log', 'loki_stdout.log'
    ]
    for task in task_data.get('tasks'):
      interesting_task_paths = []
      # Current task's identifier.
      task_id = task.get('id')
      # saved_paths may be set to None
      saved_paths = task.get('saved_paths') or []
      for path in saved_paths:
        for suffix in interesting_suffixes:
          if path.endswith(suffix):
            interesting_task_paths.append(path)
      result[task_id] = interesting_task_paths

    return result

  def _FilterTarMembers(self, tgzfile: tarfile.TarFile,
                        saved_paths: List[str]) -> List[tarfile.TarInfo]:
    """Filters a Turbinia output file and returns a list of TarInfo objects
    
    Pre-condition: tgzfile must be a valid TarFile object.

    Args:
      tgzfile: A TarFile object of a Turbinia task output file.
      saved_paths: A list of saved paths from a Turbinia task.

    Returns:
      A list of TarInfo objects.
    """
    members = []
    names = tgzfile.getnames()
    for saved_path in saved_paths:
      saved_path = saved_path.lstrip('/')
      if saved_path in names:
        members.append(tgzfile.getmember(saved_path))
    return members

  def _ExtractFiles(self, file_path: str, saved_paths: List[str]) -> List[str]:
    """Extracts files which appear in a Turbinia task's saved_paths attribute
    
    Pre-condition(s): The effective UID can read and write to the temporary
        directory. file_path must be a path to a valid tgz file containing
        Turbinia task output files.

    Args:
      file_path: File path of a Turbinia task output file (tgz).
      saved_paths: The list of saved paths from a Turbinia task.

    Returns:
      A list of local paths of each extracted file.
    """
    local_paths = []
    if not os.path.exists(file_path):
      self.logger.error(f'File not found {file_path}')
      return local_paths

    tempdir = tempfile.mkdtemp()
    with tarfile.open(file_path) as file:
      members = self._FilterTarMembers(file, saved_paths)
      file.extractall(path=tempdir, members=members)

    for saved_path in saved_paths:
      local_path = os.path.join(tempdir, saved_path.lstrip('/'))
      local_paths.append(local_path)
    return local_paths

  def _DownloadFilesFromAPI(
      self, task_data: Dict[str, List[str]]) -> List[Tuple[str, str]]:
    """Downloads task output data from the Turbinia API server. 

    Args:
      task_data: Response from a /api/request/{request_id} API call.

    Returns:
      A list of local paths to Turbinia task output files.
    """
    local_paths = []
    tasks_to_collect = self._DeterminePaths(task_data)
    api_instance = turbinia_request_results_api.TurbiniaRequestResultsApi(
        self.client)
    for task_id, saved_paths in tasks_to_collect.items():
      try:
        api_response = api_instance.get_task_output(
            task_id, _preload_content=False)
        filename = f'{task_id}.tgz'
        # Read the response and save into a local file.
        file = tempfile.NamedTemporaryFile(
            mode='wb', prefix=f'{filename}', suffix='.tgz', delete=False)
        local_path = file.name
        self.logger.info(f'Saving output for task {task_id} to: {local_path}')
        for chunk in api_response.read_chunked():
          file.write(chunk)
        file.close()

        for path in self._ExtractFiles(local_path, saved_paths):
          if os.path.exists(path):
            local_paths.append(path)
        self.logger.debug(
            f'local_paths after extracting {task_id}, {local_paths}')
      except turbinia_api_lib.ApiException as exception:
        self.logger.error(f'{exception.body}')
        raise TurbiniaException from exception
      except OSError as exception:
        self.logger.error(f'Unable to save file: {exception}')
        raise TurbiniaException from exception

    return local_paths

  def TurbiniaSetUp(
      self, project: str, turbinia_auth: bool, turbinia_recipe: Union[str,
                                                                      None],
      turbinia_zone: str, incident_id: int) -> None:
    """Sets up the object attributes.

    Raises:
      TurbiniaException: For errors in setting up the Turbinia client.

    Args:
      project (str): name of the GCP project containing the disk to process.
      turbinia_recipe (str): Turbinia recipe name.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      incident_id (int): The Timesketch sketch ID.
    """
    self.project = project
    self.turbinia_recipe = turbinia_recipe
    self.turbinia_zone = turbinia_zone
    self.incident_id = int(incident_id)
    self._output_path = tempfile.mkdtemp()
    if turbinia_auth:
      self._client_config.access_token = auth_helper.get_oauth2_credentials(
          self.credentials_path, self.client_secrets_path)
    self.client = turbinia_api_lib.ApiClient(self._client_config)

  def TurbiniaStart(
      self,
      evidence: Dict[str, Any],
      threat_intel_indicators: Optional[List[Optional[str]]] = None,
      yara_rules: Optional[List[str]] = None) -> str:
    """Creates and sends a Turbinia processing request.

    Args:
      evidence: The evidence to process.
      threat_intel_indicators: list of strings used as regular expressions in
          the Turbinia grepper module.
      yara_rules: List of Yara rule strings to use in the Turbinia Yara module.
    Returns:
      Turbinia request ID.
    """
    request_id = None
    api_instance = turbinia_requests_api.TurbiniaRequestsApi(self.client)
    yara_text = ''
    jobs_denylist = [
        'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob', 'PhotorecJob'
    ]
    evidence_name = evidence.get('type')
    if yara_rules:
      yara_text = self.DEFAULT_YARA_MODULES + '\n'.join(list(yara_rules))

    # Build request and request_options objects to send to the API server.
    request_options = {
        'filter_pattern': threat_intel_indicators,
        'jobs_denylist': jobs_denylist,
        'reason': f'{self.incident_id}',
        'requester': getpass.getuser(),
        'sketch_id': self.incident_id,
        'yara_rules': yara_text
    }

    if self.turbinia_recipe:
      request_options['recipe_name'] = self.turbinia_recipe
      # Remove incompatible options
      request_options.pop('filter_pattern')
      request_options.pop('jobs_denylist')
      request_options.pop('jobs_allowlist')

    request = {'evidence': evidence, 'request_options': request_options}

    # Send the request to the API server.
    self.logger.debug(f'Request: {request}')
    try:
      response = api_instance.create_request(request)
      request_id = response.get('request_id')
      self.logger.success(
          'Creating Turbinia request {0!s} with evidence {1!s}'.format(
              request_id, evidence_name))
    except turbinia_api_lib.ApiException as exception:
      self.ModuleError(str(exception), critical=True)
    return request_id  
  def TurbiniaWait(self, request_id: str) -> Tuple[Dict[str, Any], str]:
    """Waits for Turbinia Request to finish.

    Args:
      request_id: Request ID for the Turbinia Job.

    Returns:
      The Turbinia task data.
    """
    interval = 30
    request_data = {}
    report = ''
    retries = 0
    status = 'running'
    api_instance = turbinia_requests_api.TurbiniaRequestsApi(self.client)
    while status == 'running' and retries < 3:
      time.sleep(interval)
      try:
        request_data = api_instance.get_request_status(request_id)
        status = request_data.get('status')
        self.logger.info(f'Turbinia request {request_id} {status}')

      except turbinia_api_lib.ApiException as exception:
        retries += 1
        if exception.status == 404:
          self.logger.error(f'Request not found: {exception}. Retrying...')
      except TypeError as exception:
        self.logger.info(f'Error generating markdown report. {exception}')

    if request_data:
      report = turbinia_formatter.RequestMarkdownReport(
          request_data=request_data).generate_markdown()
    return request_data, report
