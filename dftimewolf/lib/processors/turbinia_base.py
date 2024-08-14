"""Base class for turbinia interactions."""

import getpass
import json
import os
import tarfile
import tempfile
import time
import traceback
import math

from typing import Dict, List, Optional, Tuple, Any, Union, Iterator
from pathlib import Path

from google_auth_oauthlib import flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth import exceptions as google_exceptions

import turbinia_api_lib
from turbinia_client.helpers import formatter as turbinia_formatter
from turbinia_api_lib.api import (
    turbinia_requests_api, turbinia_configuration_api, turbinia_evidence_api)
from turbinia_api_lib.api import turbinia_request_results_api
from turbinia_api_lib.api_response import ApiResponse

from dftimewolf.lib.logging_utils import WolfLogger
from dftimewolf.lib import module
# pylint: disable=unused-import
from dftimewolf.lib import state as state_lib

WAITING_STATES = frozenset(['pending', 'running'])

# mypy: disable-error-code="attr-defined"
# pylint: disable=abstract-method,no-member
class TurbiniaProcessorBase(module.BaseModule):
  """Base class for processing with Turbinia.

  Attributes:
    client (turbinia_api_lib.api_client.ApiClient): Turbinia client.
    client_config (dict): Turbinia client config.
    credentials google.oauth2.credentials.Credentials: User Oauth2 credentials.
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
  HTTP_TIMEOUT = (30, 600) # Connection, Read timeout in seconds.

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
    self.client: Optional[turbinia_api_lib.api_client.ApiClient] = None
    # pylint: disable=line-too-long
    self.client_config: Optional[turbinia_api_lib.configuration.Configuration] = None
    self.client_secrets_path = os.path.join(
        os.path.expanduser('~'), ".dftimewolf_turbinia_secrets.json")
    self.credentials_path = os.path.join(
        os.path.expanduser('~'), ".dftimewolf_turbinia.token")
    self.credentials: Optional[Credentials] = None
    self.critical = critical
    self.extensions = [
        '.plaso', 'BinaryExtractorTask.tar.gz', 'hashes.json',
        'fraken_stdout.log', 'loki_stdout.log'
    ]
    self.instance = None
    self.incident_id = str()
    self.logger = logger
    self.name = name if name else self.__class__.__name__
    self.output_path = str()
    self.parallel_count = 5  # Arbitrary, used by ThreadAwareModule
    self.project = str()
    self.requests_api_instance: turbinia_requests_api.TurbiniaRequestsApi = None # type: ignore
    self.results_api_instance: turbinia_request_results_api.TurbiniaRequestResultsApi = None # type: ignore
    self.evidence_api_instance: turbinia_evidence_api.TurbiniaEvidenceApi = None # type: ignore
    self.sketch_id = int()
    self.state = state
    self.turbinia_auth: bool = False
    self.turbinia_recipe = str()  # type: Any
    self.turbinia_region = None
    self.turbinia_zone = str()
    self.turbinia_api = str()
    os.environ['GRPC_POLL_STRATEGY'] = 'poll'

  def _decode_api_response(self, data: Any) -> Any:
    """Decodes ApiResponse data into a Python object."""
    if not isinstance(data, ApiResponse):
      return data
    data_attribute = None
    response = ''
    try:
      if data_attribute := getattr(data, 'data'):
        response = data_attribute
      if not data_attribute:
        if data_attribute := getattr(data, 'raw_data'):
          response = json.loads(data_attribute)
    except (
        AttributeError, json.JSONDecodeError) as exception:
      self.ModuleError(str(exception), critical=True)
    return response

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
      path_to_collect: A saved path from a Turbinia task.

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

  def UploadEvidence(self, file_path: Path) -> Optional[str]:
    """Uploads files to Turbinia via the API server.
    
    Args:
      file_path: Path to the file to be uploaded.
      
    Returns:
      File path to the uploaded file.
    """
    path_str = file_path.as_posix()
    turbinia_evidence_path: str = ''
    if not file_path.exists():
      self.ModuleError(f'File {path_str} not found.', critical=True)
    if self.RefreshClientCredentials():
      self.evidence_api_instance = turbinia_evidence_api.TurbiniaEvidenceApi(
          self.client)
    self.PublishMessage(
        f'Uploading evidence at {path_str} for incident {self.incident_id}'
    )
    self.logger.info(f'Incident ID: {self.incident_id}')
    api_response = self.evidence_api_instance.upload_evidence_with_http_info(
        [path_str], self.incident_id
    )
    if not api_response:
      self.ModuleError(f'Error uploading file {path_str}', critical=True)
    data: str = str(api_response.raw_data)
    try:
      response = json.loads(data)
    except json.JSONDecodeError as exception:
      self.logger.error(f'Error decoding API response: {exception}')
      return turbinia_evidence_path
    if not response:
      self.logger.error('Did not receive a response from the API server.')
      return turbinia_evidence_path
    # The API supports multiple file upload, but we're only sending one.
    file = response[0]
    turbinia_evidence_path = file.get('file_path')
    self.PublishMessage(
        f'Uploaded {file.get("original_name")} to {turbinia_evidence_path}'
    )
    return turbinia_evidence_path

  def DownloadFilesFromAPI(self, task_data: Dict[str, List[str]],
                           path: str) -> Optional[str]:
    """Downloads task output data from the Turbinia API server.

    Args:
      task_data: Response from a /api/request/{request_id} API call.
      path: A saved path from a Turbinia task.

    Returns:
      A local path to Turbinia task output files or None if files
        could not be downloaded.
    """
    result = None
    if self.RefreshClientCredentials():
      self.results_api_instance = (
          turbinia_request_results_api.TurbiniaRequestResultsApi(self.client))
    task_id = task_data.get('id')
    filename = f'{task_id}-'
    retries = 0
    # pylint: disable=line-too-long
    self.PublishMessage(f"Downloading output for task {task_id}")
    while retries < 3:
      try:
        api_response = self.results_api_instance.get_task_output_with_http_info(
            task_id,  _preload_content=False, _request_timeout=self.HTTP_TIMEOUT)  # type: ignore

        # Read the response and write to the file.
        if api_response and api_response.raw_data:
          # Create a temporary file to write the response to.
          file = tempfile.NamedTemporaryFile(
              mode='wb', prefix=f'{filename}', suffix='.tgz', delete=False)
          local_path = file.name
          self.PublishMessage(f'Saving output for task {task_id} to {local_path}')
          file.write(api_response.raw_data)
          file.close()

          # Extract the files from the tgz file.
          extracted_path = self._ExtractFiles(local_path, path)
          if os.path.exists(extracted_path):
            result = extracted_path
            self.logger.info(f"Extracted output of task {task_id} to {result}")
          return result
      except (turbinia_api_lib.exceptions.ApiException,
          turbinia_api_lib.exceptions.UnauthorizedException) as exception:
        retries += 1
        trace = traceback.format_exc()
        self.logger.warning(f'Retrying after 3 seconds: {exception}{trace}')
        time.sleep(3)
      except OSError as exception:
        self.ModuleError(f'Unable to write to file: {exception}', critical=True)

    if not result:
      self.ModuleError(f'Unable to download data for task {task_id}', critical=True)

    return result

  def GetCredentials(self, credentials_path: str,
                     client_secrets_path: str) -> Optional[Credentials]:
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
          'Could not find existing credentials. Requesting new tokens.'
      )
      try:
        appflow = flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_path, scopes
        )
        if appflow:
          appflow.run_local_server(
              host='localhost', port=8888, open_browser=False
          )
          credentials = appflow.credentials
      except FileNotFoundError as exception:
        msg = f'Client secrets file not found: {exception!s}'
        self.ModuleError(msg, critical=True)

      self.logger.info(
          'Starting local HTTP server on localhost:8888 for OAUTH flow. '
          'If running dftimewolf remotely over SSH you will need to tunnel '
          'port 8888.'
      )

    # Save credentials
    if credentials:
      with open(credentials_path, 'w', encoding='utf-8') as token:
        token.write(credentials.to_json())

    return credentials

  def RefreshClientCredentials(self) -> bool:
    """Refreshes credentials and initializes new API client."""
    if not self.turbinia_auth:
      return False

    refresh = False
    if self.credentials and self.credentials.expired:
      self.logger.warning(
        "Turbinia credentials invalid or expired. Re-authenticating..."
      )
      self.credentials = self.GetCredentials(
          self.credentials_path, self.client_secrets_path)
      self.client = self.InitializeTurbiniaApiClient(self.credentials)
      refresh = True
    return bool(refresh)

  def InitializeTurbiniaApiClient(
      self,
      credentials: Optional[Credentials]
    ) -> turbinia_api_lib.api_client.ApiClient:
    """Creates a Turbinia API client object.

    This method also runs the authentication flow if needed.

    Returns:
      turbinia_api_lib.api_client.ApiClient: A Turbinia API client object.
    """
    self.client_config = turbinia_api_lib.configuration.Configuration(
        host=self.turbinia_api)
    self.client_config.retries = 3 # type: ignore
    if not self.client_config:
      self.ModuleError('Unable to configure Turbinia API server', critical=True)
    # Check if Turbinia requires authentication.
    if self.turbinia_auth:
      if not credentials:
        self.credentials = self.GetCredentials(
            self.credentials_path, self.client_secrets_path)
      if self.credentials and self.credentials.id_token:
        self.client_config.access_token = self.credentials.id_token
      else:
        self.ModuleError(
            'Unable to obtain id_token from identity provider', critical=True)
    return turbinia_api_lib.api_client.ApiClient(self.client_config)

  def TurbiniaSetUp(
      self, project: str, turbinia_recipe: Union[str, None], turbinia_zone: str,
      turbinia_api: str, incident_id: str, sketch_id: int,
      turbinia_auth: bool = False) -> None:
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
    self.client_config = turbinia_api_lib.configuration.Configuration(
      host=self.turbinia_api)
    self.client = self.InitializeTurbiniaApiClient(self.credentials)
    self.requests_api_instance = turbinia_requests_api.TurbiniaRequestsApi(
        self.client)
    self.results_api_instance = (
        turbinia_request_results_api.TurbiniaRequestResultsApi(self.client))
    self.evidence_api_instance = (
        turbinia_evidence_api.TurbiniaEvidenceApi(self.client))
    # We need to get the output path from the Turbinia server.
    api_instance = turbinia_configuration_api.TurbiniaConfigurationApi(
        self.client)
    try:
      api_response = api_instance.read_config_with_http_info()
      decoded_response = self._decode_api_response(api_response)
      self.output_path = decoded_response.get('OUTPUT_DIR')
    except turbinia_api_lib.exceptions.ApiException as exception:
      self.logger.info("Error connecting to Turbinia API server, please "
          "make sure you configured the Turbinia recipe "
          "parameters correctly.")
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
        'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob',
        'PhotorecJob', 'PsortJob'
    ]
    if not evidence:
      self.ModuleError('No evidence to process', critical=True)

    evidence_name = evidence.get('type')
    if yara_rules:
      yara_text = self.DEFAULT_YARA_MODULES + '\n'.join(list(yara_rules))

    # Build request and request_options objects to send to the API server.
    request_options: Dict[str, Any] = {
        'filter_pattern': threat_intel_indicators,
        'jobs_allowlist': [],
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
      try:
        request_options.pop('filter_pattern')
        request_options.pop('jobs_denylist')
        request_options.pop('jobs_allowlist')
      except KeyError as exception:
        self.logger.debug(f'Key: {exception} not found in request options.')

    request = {'evidence': evidence, 'request_options': request_options}

    # Send the request to the API server.
    try:
      # Refresh token if needed
      if self.RefreshClientCredentials():
        self.requests_api_instance = (
            turbinia_requests_api.TurbiniaRequestsApi(self.client)
        )
      api_response = self.requests_api_instance.create_request_with_http_info(
        request) # type: ignore
      decoded_response = self._decode_api_response(api_response)
      request_id = decoded_response.get('request_id')
      evidence_type: str = evidence.get('type', '')
      if evidence_type.lower() == 'googleclouddisk':
        evidence_path = evidence.get('disk_name')
      elif evidence_type.lower() in ('rawdisk', 'compresseddirectory'):
        evidence_path = evidence.get('source_path')
      else:
        evidence_path = 'unknown'
      self.logger.info(
        f"Creating Turbinia request {str(request_id)} with "
        f"evidence {str(evidence_name)} at {evidence_path}"
      )
      self.logger.debug(
        "Turbinia request status at {0!s}".format(self.turbinia_api)
      )
    except turbinia_api_lib.exceptions.ApiException as exception:
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
    wait_status = ['running', 'pending']
    if not request_id:
      self.ModuleError('No request ID provided', critical=True)

    while status in wait_status and retries < 3:
      time.sleep(interval)
      try:
        # Refresh token if needed
        if self.RefreshClientCredentials():
          self.requests_api_instance = (
              turbinia_requests_api.TurbiniaRequestsApi(self.client)
          )
        request_data = (
          self.requests_api_instance.get_request_status_with_http_info(
            request_id))
        request_data = self._decode_api_response(request_data)
        status = request_data.get('status')
        failed_tasks = request_data.get('failed_tasks')
        successful_tasks = request_data.get('successful_tasks')
        task_count = request_data.get('task_count')
        progress = math.ceil(
            ((failed_tasks + successful_tasks) / task_count) * 100
        )
        self.logger.info(
          f"Turbinia request {request_id} is {status}. Progress: {progress}%"
        )

        for task in request_data.get('tasks', []):
          current_saved_paths = task.get('saved_paths', [])
          if not current_saved_paths:
            continue
          for path in current_saved_paths:
            if (
                path not in processed_paths
                and self._isInterestingPath(path)
                and path.startswith(self.output_path)
            ):
              processed_paths.add(path)
              yield task, path

      except (turbinia_api_lib.exceptions.ApiException,
          turbinia_api_lib.exceptions.UnauthorizedException) as exception:
        retries += 1
        self.logger.warning(f'Retrying after 3 seconds: {exception.body}')
        time.sleep(3)

  def TurbiniaFinishReport(self,
                           request_id: str,
                           priority_filter: int) -> Optional[str]:
    """This method generates a report for a Turbinia request."""
    # Refresh token if needed
    if self.RefreshClientCredentials():
      self.requests_api_instance = turbinia_requests_api.TurbiniaRequestsApi(
          self.client
      )
    request_data = (
        self.requests_api_instance.get_request_status_with_http_info(
            request_id))
    request_data = self._decode_api_response(request_data)
    if request_data:
      report: str = turbinia_formatter.RequestMarkdownReport(
          request_data=request_data
      ).generate_markdown(priority_filter=priority_filter)
      return report
    return None
