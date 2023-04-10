# -*- coding: utf-8 -*-
"""Base class for turbinia interactions."""

import getpass
import os
import tarfile
import tempfile
import time
from typing import Dict, List, Optional, Tuple, Any, Union, Generator

import turbinia_api_lib
from turbinia_client.helpers import auth_helper
from turbinia_client.helpers import formatter as turbinia_formatter
from turbinia_api_lib.api import (turbinia_requests_api,
                                  turbinia_configuration_api)
from turbinia_api_lib.api import turbinia_request_results_api

from dftimewolf.lib.logging_utils import WolfLogger
from dftimewolf.lib import module


# pylint: disable=abstract-method,no-member
class TurbiniaAPIProcessorBase(module.BaseModule):
  """Base class for processing with Turbinia.

  Attributes:
    client (TurbiniaClient): Turbinia client.
    instance (str): name of the Turbinia instance
    project (str): name of the GCP project containing the disk to process.
    sketch_id (int): The Timesketch sketch id
    turbinia_recipe (str): Turbinia recipe name.
    turbinia_region (str): GCP region in which the Turbinia server is running.
    turbinia_zone (str): GCP zone in which the Turbinia server is running.
    turbinia_api (str): Turbinia API endpoint.
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
    self.output_path = str()
    self.client = None
    self.instance = None
    self.project = str()
    self.incident_id = str()
    self.sketch_id = int()
    self.turbinia_auth = bool()
    self.turbinia_recipe = str()  # type: Any
    self.turbinia_region = None
    self.turbinia_zone = str()
    self.turbinia_api = str()
    self.client_config = None
    self.parallel_count = 5  # Arbitrary, used by ThreadAwareModule
    self.logger = logger
    self.extentions = [
        '.plaso', 'BinaryExtractorTask.tar.gz', 'hashes.json',
        'fraken_stdout.log', 'loki_stdout.log'
    ]
    os.environ['GRPC_POLL_STRATEGY'] = 'poll'

  def _isInterestingPath(self, path):
    """Checks if a path is interesting for the processor."""
    for suffix in self.extentions:
      return bool(path.endswith(suffix))

  def _FilterTarMembers(
      self, tgzfile: tarfile.TarFile, path_to_collect: str) -> tarfile.TarInfo:
    """Filters a TarFile object for a specific path.
    
    Pre-condition: tgzfile must be a valid TarFile object.

    Args:
      tgzfile: A TarFile object of a Turbinia task output file.
      saved_paths: A list of saved paths from a Turbinia task.

    Returns:
      A list of TarInfo objects.
    """
    members = []
    names = tgzfile.getnames()
    path_to_collect = path_to_collect.lstrip('/')
    if path_to_collect in names:
      members.append(tgzfile.getmember(path_to_collect))
    return members

  def _ExtractFiles(self, tgz_path: str, path_to_collect: str) -> List[str]:
    """Extracts files which appear in a Turbinia task's saved_paths attribute
    
    Pre-condition(s): The effective UID can read and write to the temporary
        directory. file_path must be a path to a valid tgz file containing
        Turbinia task output files.

    Args:
      file_path: File path of a Turbinia task output file (tgz).
      paths_to_collect: A saved path from a Turbinia task.

    Returns:
      A local path to the extracted file.
    """
    local_path = ''
    if not os.path.exists(tgz_path):
      self.logger.error(f'File not found {tgz_path}')
      return local_path

    tempdir = tempfile.mkdtemp()
    with tarfile.open(tgz_path) as file:
      members = self._FilterTarMembers(file, path_to_collect)
      file.extractall(path=tempdir, members=members)

    local_path = os.path.join(tempdir, path_to_collect.lstrip('/'))
    return local_path

  def _DownloadFilesFromAPI(
      self, task_data: Dict[str, List[str]], path: str) -> str:
    """Downloads task output data from the Turbinia API server. 

    Args:
      task_data: Response from a /api/request/{request_id} API call.

    Returns:
      A local path to Turbinia task output files.
    """
    api_instance = turbinia_request_results_api.TurbiniaRequestResultsApi(
        self.client)
    try:
      task_id = task_data.get('id')
      api_response = api_instance.get_task_output(
          task_id, _preload_content=False)
      filename = f'{task_id}.tgz'

      # Create a temporary file to write the response to.
      file = tempfile.NamedTemporaryFile(
          mode='wb', prefix=f'{filename}', suffix='.tgz', delete=False)
      local_path = file.name
      self.logger.info(f'Saving output for task {task_id} to: {local_path}')
      # Read the response in chunks and write to the file.
      for chunk in api_response.read_chunked():
        file.write(chunk)
      file.close()

      # Extract the files from the tgz file.
      extracted_path = self._ExtractFiles(local_path, path)
      if os.path.exists(extracted_path):
        return extracted_path

    except turbinia_api_lib.ApiException as exception:
      self.ModuleError(
        f'Unable to download task data: {exception}', critical=False)
    except OSError as exception:
      self.ModuleError(f'Unable to write to file: {exception}', critical=False)

  def TurbiniaSetUp(
      self, project: str, turbinia_auth: bool,
      turbinia_recipe: Union[str, None], turbinia_zone: str, turbinia_api: str,
      incident_id: str, sketch_id: int) -> None:
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
    self.turbinia_auth = turbinia_auth
    self.turbinia_api = turbinia_api
    self.turbinia_recipe = turbinia_recipe
    self.turbinia_zone = turbinia_zone
    self.incident_id = incident_id
    self.sketch_id = sketch_id
    self.client_config = turbinia_api_lib.Configuration(host=self.turbinia_api)
    # Check if Turbinia requires authentication.
    if self.turbinia_auth:
      self.client_config.access_token = auth_helper.get_oauth2_credentials(
          self.credentials_path, self.client_secrets_path)
    self.client = turbinia_api_lib.ApiClient(self.client_config)

    # We need to get the output path from the Turbinia server.
    api_instance = turbinia_configuration_api.TurbiniaConfigurationApi(
        self.client)
    try:
      api_response = api_instance.read_config()
      self.output_path = api_response.get('OUTPUT_DIR')
    except turbinia_api_lib.ApiException as exception:
      self.ModuleError({exception}, critical=True)

  def TurbiniaStart(
      self,
      evidence: Dict[str, Any],
      threat_intel_indicators: Optional[List[Optional[str]]] = None,
      yara_rules: Optional[List[str]] = None) -> str:
    """Sends a Turbinia processing request to the Turbinia API server.

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
        'reason': self.incident_id,
        'requester': getpass.getuser(),
        'yara_rules': yara_text
    }
    if self.sketch_id:
      request_options['sketch_id'] = self.sketch_id

    if self.turbinia_recipe:
      request_options['recipe_name'] = self.turbinia_recipe
      # Remove incompatible options
      request_options.pop('filter_pattern')
      request_options.pop('jobs_denylist')
      request_options.pop('jobs_allowlist')

    request = {'evidence': evidence, 'request_options': request_options}

    # Send the request to the API server.
    try:
      response = api_instance.create_request(request)
      request_id = response.get('request_id')
      self.logger.success(
          'Creating Turbinia request {0!s} with evidence {1!s}'.format(
              request_id, evidence_name))
    except turbinia_api_lib.ApiException as exception:
      self.ModuleError(str(exception), critical=True)
    return request_id

  def TurbiniaWait(
      self,
      request_id: str) -> Generator[Tuple[Dict[str, Any], str], None, None]:
    """This method waits until a Turbinia request finishes processing.

    On each iteration, it checks the status of the request and yields each task
    data and the paths that have not been processed in prior iterations. A path
    is only considered if it is not already processed, if it is interesting
    (i.e., not a log file or a temporary file), and if it starts with the
    Turbinia server configured output path.

    The method retries 3 times if there is an API exception.

    Args:
        request_id: Request ID for the Turbinia Job.

    Yields:
        A tuple containing the Turbinia task data and the path that has not been
          processed yet.
    """

    interval = 30
    retries = 0
    processed_paths = set()
    api_instance = turbinia_requests_api.TurbiniaRequestsApi(self.client)
    status = 'running'
    while status == 'running' and retries < 3:
      time.sleep(interval)
      try:
        request_data = api_instance.get_request_status(request_id)
        status = request_data.get('status')
        self.logger.info(f'Turbinia request {request_id} {status}')

        for task in request_data.get('tasks', []):
          current_saved_paths = task.get('saved_paths', [])
          task_id = task.get('id')
          if not current_saved_paths:
            continue

          for path in current_saved_paths:
            if path not in processed_paths and self._isInterestingPath(
                path) and path.startswith(self.output_path):
              processed_paths.add(path)
              self.logger.info(
                  f'New output file {path} found for task {task_id}')
              yield task, path

      except turbinia_api_lib.ApiException as exception:
        retries += 1
        self.logger.warning(f'Retrying after exception: {exception.body}')

  def TurbiniaFinishReport(self, request_id: str) -> Dict[str, Any]:
    """This method generates a Turbinia report for a given request ID."""
    api_instance = turbinia_requests_api.TurbiniaRequestsApi(self.client)
    request_data = api_instance.get_request_status(request_id)
    if request_data:
      report = turbinia_formatter.RequestMarkdownReport(
          request_data=request_data).generate_markdown()
    return report
