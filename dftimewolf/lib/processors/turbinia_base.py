"""Base class for turbinia interactions."""

import getpass
import os
import tarfile
import tempfile
import time
import math

from typing import Dict, List, Optional, Tuple, Any, Union, Iterator

from google_auth_oauthlib import flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth import exceptions as google_exceptions

import turbinia_api_lib
from turbinia_client.helpers import formatter as turbinia_formatter
from turbinia_api_lib.api import (
    turbinia_requests_api, turbinia_configuration_api)
from turbinia_api_lib.api import turbinia_request_results_api

from dftimewolf.lib.logging_utils import WolfLogger
from dftimewolf.lib import module
# pylint: disable=unused-import
from dftimewolf.lib import state as state_lib


# pylint: disable=abstract-method,no-member
class TurbiniaProcessorBase(module.BaseModule):
  """Base class for processing with Turbinia.

  Attributes:
    client (turbinia_api_lib.ApiClient): Turbinia client.
    client_config (dict): Turbinia client config.
    extensions (List[str]): List of file extensions to look for.
    incident_id (str): The Timesketch incident id.
    instance (str): name of the Turbinia instance
    logger (WolfLogger): logger.
    project (str): name of the GCP project containing the disk to process.
    requests_api_instance (turbinia_requests_api.TurbiniaRequestsApi):
        Turbinia requests API instance.
    sketch_id (int): The Timesketch sketch id
    turbinia_recipe (str): Turbinia recipe name.
    turbinia_region (str): GCP region in which the Turbinia server is running.
    turbinia_zone (str): GCP zone in which the Turbinia server is running.
    turbinia_api (str): Turbinia API endpoint.
    turbinia_auth (bool): Turbinia auth flag.
    parallel_count (int): Number of threads to use.
  """

  DEFAULT_YARA_MODULES = 'import "pe"\nimport "math"\nimport "hash"\n\n'

  def __init__(
      self,
      state: "state_lib.DFTimewolfState",
      logger: WolfLogger,
      name: Optional[str] = None,
      critical: bool = False,
  ) -> None:
    """Initializes a Turbinia base processor.

    Args:
      state (state.DFTimewolfState): recipe state.
      logger: A logger instance.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super().__init__(state=state, name=name, critical=critical)
    self.name = name if name else self.__class__.__name__
    self.critical = critical
    self.state = state
    self.output_path = str()
    self.client: turbinia_api_lib.ApiClient = None
    self.instance = None
    self.project = str()
    self.incident_id = str()
    self.sketch_id = int()
    self.turbinia_auth = bool()
    self.turbinia_recipe = str()  # type: Any
    self.turbinia_region = None
    self.turbinia_zone = str()
    self.turbinia_api = str()
    self.requests_api_instance: turbinia_requests_api.TurbiniaRequestsApi = None
    self.client_config = None
    self.credentials_path = os.path.join(
        os.path.expanduser('~'), ".dftimewolf_turbinia.token")
    self.client_secrets_path = os.path.join(
        os.path.expanduser('~'), ".dftimewolf_turbinia_secrets.json")
    self.parallel_count = 5  # Arbitrary, used by ThreadAwareModule
    self.logger = logger
    self.extensions = [
        '.plaso', 'BinaryExtractorTask.tar.gz', 'hashes.json',
        'fraken_stdout.log', 'loki_stdout.log'
    ]
    os.environ['GRPC_POLL_STRATEGY'] = 'poll'

  def _isInterestingPath(self, path: str) -> bool:
    """Checks if a path is interesting for the processor."""
    for suffix in self.extensions:
      if path.endswith(suffix):
        return True
    return False

  def _FilterTarMembers(self, tgzfile: tarfile.TarFile,
                        path_to_collect: str) -> List[tarfile.TarInfo]:
    """Filters a TarFile object for a specific path.

    Pre-condition: tgzfile must be a valid TarFile object.

    Args:
      tgzfile: A TarFile object of a Turbinia task output file.
      path_to_collect: A path from a Turbinia task.

    Returns:
      A list of TarInfo objects.
    """
    members = []
    names = tgzfile.getnames()
    path_to_collect = path_to_collect.lstrip('/')
    if path_to_collect in names:
      members.append(tgzfile.getmember(path_to_collect))
    return members

  def _ExtractFiles(self, tgz_path: str, path_to_collect: str) -> str:
    """Extracts files which appear in a Turbinia task's saved_paths attribute

    Pre-condition(s): The effective UID can read and write to the temporary
        directory. file_path must be a path to a valid tgz file containing
        Turbinia task output files.

    Args:
      tgz_path: File path of a Turbinia task output file (tgz).
      path_to_collect: A saved path from a Turbinia task.

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

  def DownloadFilesFromAPI(self, task_data: Dict[str, List[str]],
                           path: str) -> Optional[str]:
    """Downloads task output data from the Turbinia API server.

    Args:
      task_data: Response from a /api/request/{request_id} API call.

    Returns:
      A local path to Turbinia task output files or None if files
        could not be downloaded.
    """
    result = None
    api_instance = turbinia_request_results_api.TurbiniaRequestResultsApi(
        self.client)
    try:
      task_id = task_data.get('id')
      api_response = api_instance.get_task_output(
          task_id, _preload_content=False)
      filename = f'{task_id}-'

      # Create a temporary file to write the response to.
      file = tempfile.NamedTemporaryFile(
          mode='wb', prefix=f'{filename}', suffix='.tgz', delete=False)
      local_path = file.name
      self.logger.info(
          f'Downloading output for task {task_id} to: {local_path}')
      # Read the response and write to the file.
      file.write(api_response.read())
      file.close()

      # Extract the files from the tgz file.
      extracted_path = self._ExtractFiles(local_path, path)
      if os.path.exists(extracted_path):
        result = extracted_path
      self.PublishMessage(
          f'Extracted output file to {local_path} for task {task_id}')
    except turbinia_api_lib.ApiException as exception:
      self.ModuleError(
          f'Unable to download task data: {exception}', critical=False)
    except OSError as exception:
      self.ModuleError(f'Unable to write to file: {exception}', critical=False)

    return result

  def GetCredentials(self, credentials_path: str,
                     client_secrets_path: str) -> Optional[Any]:
    """Authenticates the user using Google OAuth services."""
    scopes = ['openid', 'https://www.googleapis.com/auth/userinfo.email']
    credentials = None

    # Load credentials file if it exists
    if os.path.exists(credentials_path):
      try:
        credentials = Credentials.from_authorized_user_file(
            credentials_path, scopes)
      except ValueError as exception:
        msg = f'Error loading credentials: {exception!s}'
        self.ModuleError(msg, critical=True)
      # Refresh credentials using existing refresh_token
      if credentials and credentials.refresh_token:
        self.logger.debug('Found a refresh token. Requesting new id_token...')
        try:
          credentials.refresh(Request())
        except google_exceptions.RefreshError as exception:
          self.logger.debug(f'Error refreshing credentials: {exception!s}')
    else:
      # No credentials file, acquire new credentials from secrets file.
      self.logger.debug(
          'Could not find existing credentials. Requesting new tokens.')
      try:
        appflow = flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_path, scopes)
      except FileNotFoundError as exception:
        msg = f'Client secrets file not found: {exception!s}'
        self.ModuleError(msg, critical=True)

      self.logger.info(
          'Starting local HTTP server on localhost:8888 for OAUTH flow. '
          'If running dftimewolf remotely over SSH you will need to tunnel '
          'port 8888.')
      appflow.run_local_server(host='localhost', port=8888)
      credentials = appflow.credentials

      # Save credentials
      with open(credentials_path, 'w', encoding='utf-8') as token:
        token.write(credentials.to_json())

    if credentials:
      return credentials.id_token

    return credentials

  def TurbiniaSetUp(
      self, project: str, turbinia_auth: bool,
      turbinia_recipe: Union[str, None], turbinia_zone: str, turbinia_api: str,
      incident_id: str, sketch_id: int) -> None:
    """Sets up the object attributes.

    Args:
      project (str): name of the GCP project containing the disk to process.
      turbinia_auth (bool): Turbinia auth flag.
      turbinia_recipe (str): Turbinia recipe name.
      turbinia_zone (str): GCP zone in which the Turbinia server is running.
      turbinia_api (str): URL of the Turbinia API server.
      incident_id (str): The incident ID.
      sketch_id (int): The sketch ID.
    """
    self.project = project
    self.turbinia_auth = turbinia_auth
    self.turbinia_api = turbinia_api
    self.turbinia_recipe = turbinia_recipe
    self.turbinia_zone = turbinia_zone
    self.incident_id = incident_id
    self.sketch_id = sketch_id
    self.client_config = turbinia_api_lib.Configuration(host=self.turbinia_api)
    if not self.client_config:
      self.ModuleError('Unable to configure Turbinia API server', critical=True)
      return
    # Check if Turbinia requires authentication.
    if self.turbinia_auth:
      self.client_config.access_token = self.GetCredentials(
          self.credentials_path, self.client_secrets_path)
      if not self.client_config.access_token:
        self.ModuleError(
            'Unable to authenticate to Turbinia API server', critical=True)
    self.client = turbinia_api_lib.ApiClient(self.client_config)
    self.requests_api_instance = turbinia_requests_api.TurbiniaRequestsApi(
        self.client)
    # We need to get the output path from the Turbinia server.
    api_instance = turbinia_configuration_api.TurbiniaConfigurationApi(
        self.client)
    try:
      api_response = api_instance.read_config()
      self.output_path = api_response.get('OUTPUT_DIR')
    except turbinia_api_lib.ApiException as exception:
      self.ModuleError(exception.body, critical=True)

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
      Turbinia request identifier.
    """
    request_id = ''
    yara_text = ''
    jobs_denylist = [
        'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob', 'PhotorecJob'
    ]
    if not evidence:
      self.ModuleError('No evidence to process', critical=True)

    evidence_name = evidence.get('type')
    if yara_rules:
      yara_text = self.DEFAULT_YARA_MODULES + '\n'.join(list(yara_rules))

    # Build request and request_options objects to send to the API server.
    request_options: Dict[str, Any] = {
        'filter_pattern': threat_intel_indicators,
        'jobs_denylist': jobs_denylist,
        'reason': self.incident_id,
        'requester': getpass.getuser(),
        'yara_rules': yara_text
    }
    if self.sketch_id:
      request_options['sketch_id'] = int(self.sketch_id)

    if self.turbinia_recipe:
      request_options['recipe_name'] = self.turbinia_recipe
      # Remove incompatible options
      request_options.pop('filter_pattern')
      request_options.pop('jobs_denylist')
      request_options.pop('jobs_allowlist')

    request = {'evidence': evidence, 'request_options': request_options}

    # Send the request to the API server.
    try:
      response = self.requests_api_instance.create_request(request)
      request_id = response.get('request_id')
      self.logger.success(
          'Creating Turbinia request {0!s} with evidence {1!s}'.format(
              request_id, evidence_name))
    except turbinia_api_lib.ApiException as exception:
      self.ModuleError(str(exception), critical=True)

    if not request_id:
      self.ModuleError('Unable to create Turbinia request', critical=True)

    return request_id

  def TurbiniaWait(self,
                   request_id: str) -> Iterator[Tuple[Dict[str, Any], str]]:
    """This method waits until a Turbinia request finishes processing.

    On each iteration, it checks the status of the request and yields each task
    data and a path that has not been processed in prior iterations. A path
    is only considered if it is not already processed, if it is interesting
    (i.e., not a log file or a temporary file), and if its path starts with the
    Turbinia server configured output path.

    The method retries 3 times if there is an API exception.

    Args:
        request_id: Request identifier for the Turbinia Job.

    Yields:
        A tuple containing the Turbinia task data and the path that has not been
          processed yet.
    """

    interval = 30
    retries = 0
    processed_paths = set()
    status = 'running'
    running_tasks = 1
    if not request_id:
      self.ModuleError('No request ID provided', critical=True)

    while status == 'running' and running_tasks > 0 and retries < 3:
      time.sleep(interval)
      try:
        request_data = self.requests_api_instance.get_request_status(request_id)
        status = request_data.get('status')
        running_tasks = request_data.get('running_tasks')
        failed_tasks = request_data.get('failed_tasks')
        successful_tasks = request_data.get('successful_tasks')
        task_count = request_data.get('task_count')
        progress = math.ceil(
            ((failed_tasks + successful_tasks) / task_count) * 100)
        self.PublishMessage(
            f'Turbinia request {request_id} is {status}. Progress: {progress}%')

        for task in request_data.get('tasks', []):
          current_saved_paths = task.get('saved_paths', [])
          if not current_saved_paths:
            continue
          for path in current_saved_paths:
            if path not in processed_paths and self._isInterestingPath(
                path) and path.startswith(self.output_path):
              processed_paths.add(path)
              yield task, path

      except turbinia_api_lib.ApiException as exception:
        retries += 1
        self.logger.warning(f'Retrying after exception: {exception.body}')

  def TurbiniaFinishReport(self, request_id: str) -> str:
    """This method generates a report for a Turbinia request."""
    request_data = self.requests_api_instance.get_request_status(request_id)
    if request_data:
      report: str = turbinia_formatter.RequestMarkdownReport(
          request_data=request_data).generate_markdown()
    return report
