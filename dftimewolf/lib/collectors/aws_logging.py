# -*- coding: utf-8 -*-
"""Reads logs from an AWS account"""

import json
import tempfile
import datetime
from typing import Any, Dict, Optional

from boto3 import session as boto3_session
from botocore import exceptions as boto_exceptions

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class AWSLogsCollector(module.BaseModule):
  """Collector for Amazon Web Services (AWS) logs."""

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initializes an AWS logs collector."""
    super(AWSLogsCollector, self).__init__(state, name=name, critical=critical)
    self._profile_name: Optional[str] = None
    self._query_filter: Optional[str] = None
    self._start_time: Optional[datetime.datetime] = None
    self._end_time: Optional[datetime.datetime] = None
    self._region: str = None  # type: ignore

  # pylint: disable=arguments-differ
  def SetUp(self,
            region: str,
            profile_name: Optional[str]=None,
            query_filter: Optional[str]=None,
            start_time: Optional[datetime.datetime]=None,
            end_time: Optional[datetime.datetime]=None) -> None:
    """Sets up an AWS logs collector

    Args:
      region: An AWS region name.
      profile_name: Optional. The profile name to collect logs with.
      query_filter: Optional. The CloudTrail query filter in the form
        'key,value'
      start_time: Optional. The start time for the query.
      end_time: Optional. The end time for the query.
    """
    self._region = region
    self._profile_name = profile_name
    self._query_filter = query_filter
    self._start_time = start_time
    self._end_time = end_time

  def Process(self) -> None:
    """Copies logs from an AWS account."""

    output_file = tempfile.NamedTemporaryFile(
      mode='w', delete=False, encoding='utf-8', suffix='.jsonl')
    output_path = output_file.name
    self.logger.info(f"Downloading logs to {output_path:s}")

    if self._profile_name:
      try:
        session = boto3_session.Session(profile_name=self._profile_name)
      except boto_exceptions.ProfileNotFound as exception:
        self.ModuleError(f'AWS profile {self._profile_name} not found.')
        self.ModuleError(str(exception), critical=True)
    else:
      session = boto3_session.Session()

    try:
      sts_client = session.client('sts')
      sts_client.get_caller_identity()
    except (boto_exceptions.NoRegionError,
            boto_exceptions.NoCredentialsError) as exception:
      self.ModuleError('No profile found or credentials not properly '
          'configured. See https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html')  # pylint: disable=line-too-long
      self.ModuleError(str(exception), critical=True)

    cloudtrail_client = session.client('cloudtrail', region_name=self._region)

    request_params: Dict[str, Any] = {}
    if self._query_filter:
      k, v = self._query_filter.split(',')
      filters = [{'AttributeKey': k, 'AttributeValue': v}]
      request_params['LookupAttributes'] = filters
    if self._start_time:
      request_params['StartTime'] = self._start_time
    if self._end_time:
      request_params['EndTime'] = self._end_time

    while True:
      try:
        results = cloudtrail_client.lookup_events(**request_params)
        events = results.get('Events', [])
        for event in events:
          # Set the default serializer to str() to account for datetime objects.
          event_string = json.dumps(event, default=str)
          output_file.write(event_string)
          output_file.write('\n')

        next_token = results.get('NextToken')
        if not next_token:
          break
        request_params['NextToken'] = next_token
      except boto_exceptions.ClientError as exception:
        self.ModuleError('Boto3 client error, check that lookup parameters '
          'are correct https://docs.aws.amazon.com/awscloudtrail/latest/APIReference/API_LookupEvents.html')  # pylint: disable=line-too-long
        self.ModuleError(str(exception), critical=True)

    self.logger.info(f'Downloaded logs to {output_path}')
    output_file.close()

    logs_report = containers.File('AWSLogsCollector result', output_path)
    self.StoreContainer(logs_report)


modules_manager.ModulesManager.RegisterModule(AWSLogsCollector)
