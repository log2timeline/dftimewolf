# -*- coding: utf-8 -*-
"""Base class for turbinia interactions."""

import base64
import getpass
import os
import random
import tempfile
import time
from typing import Dict, List, Optional, Tuple, Any, Union

import turbinia_api_lib

from turbinia_api_lib.api import turbinia_requests_api
from turbinia_api_lib.api import turbinia_tasks_api
from turbinia_api_lib.api import turbinia_configuration_api
from turbinia_api_lib.api import turbinia_jobs_api
from turbinia_api_lib.api import turbinia_request_results_api

from dftimewolf.lib.logging_utils import WolfLogger


# pylint: disable=abstract-method,no-member
class TurbiniaProcessorBaseAPI(object):
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
    self.client = None
    self.instance = None
    self.project = str()
    self.sketch_id = int()
    self.turbinia_recipe = str()  # type: Any
    self.turbinia_region = None
    self.turbinia_zone = str()
    self.parallel_count = 5  # Arbitrary, used by ThreadAwareModule
    self.logger = logger
    self._client_config = turbinia_api_lib.Configuration(
        host="http://localhost:8000")
    os.environ['GRPC_POLL_STRATEGY'] = 'poll'

  def TurbiniaSetUp(
      self, project: str, turbinia_recipe: Union[str, None], turbinia_zone: str,
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
    self._output_path = tempfile.mkdtemp()
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
    jobs_denylist = None
    yara_text = None
    jobs_denylist = [
        'StringsJob', 'BinaryExtractorJob', 'BulkExtractorJob', 'PhotorecJob'
    ]
    evidence_name = evidence.get('type')
    if yara_rules:
      yara_text = self.DEFAULT_YARA_MODULES + '\n'.join(list(yara_rules))
    recipe_name = self.turbinia_recipe

    # Build request and request_options objects to send to the API server.
    request_options = {
        'jobs_denylist': jobs_denylist,
        'sketch_id': self.sketch_id,
        'requester': getpass.getuser(),
        'yara_rules': yara_text,
        'filter_pattern': threat_intel_indicators
    }
    if self.turbinia_recipe:
      request_options['recipe_name'] = self.turbinia_recipe
    request = {'evidence': evidence, 'request_options': request_options}

    # Send the request to the API server.
    try:
      request_id = api_instance.create_request(request)
      self.logger.success(
          'Creating Turbinia request {0:s} with Evidence {1!s}'.format(
              request_id, evidence_name))
      self.logger.info('Started Turbinia request {0:s}'.format(request_id))
    except turbinia_api_lib.exceptions.ApiException as exception:
      self.logger.error(
          f'Received status code {exception.status} '
          f'when calling create_request: {exception.body}')
    except (TypeError, turbinia_api_lib.exceptions.ApiTypeError) as exception:
      self.logger.error(f'The request object is invalid. {exception}')

    return request_id

  def TurbiniaWait(self, request_id: str) -> Tuple[List[Dict[str, str]], Any]:
    """Waits for Turbinia Request to finish.

    Args:
      request_id: Request ID for the Turbinia Job.

    Returns:
      The Turbinia task data.

    Raises:
      RuntimeError: If the Turbinia request fails for reasons not linked to
          rate limiting.
    """
    pass