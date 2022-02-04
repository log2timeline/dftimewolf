# -*- coding: utf-8 -*-
"""Reads logs from an AWS account"""

import json
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional, Union

from boto3 import session as boto3_session

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
    self._zone: str = ''
    self._profile_name: Optional[str] = None
    self._query_filter: Optional[str] = None
    self._start_time: Optional[datetime] = None
    self._end_time:Optional[datetime] = None

  # pylint: disable=arguments-differ
  def SetUp(self,
            zone: str,
            profile_name: Optional[str]=None,
            query_filter: Optional[str]=None,
            start_time: Optional[str]=None,
            end_time: Optional[str]=None) -> None:
    """Sets up an AWS logs collector

    Args:
      zone (str): default availability zone for libcloudforensics AWSAccount.
      profile_name (str): Optional. The profile name to collect logs with.
      query_filter (str): Optional. The CloudTrail query filter in the form
        'key,value'
      start_time (str): Optional. The start time for the query in the format
        'YYYY-MM-DD HH:MM:SS'
      end_time (str): Optional. The end time for the query in the format
        'YYYY-MM-DD HH:MM:SS'
    """
    self._zone = zone
    self._profile_name = profile_name
    self._query_filter = query_filter
    if start_time:
      self._start_time = datetime.fromisoformat(start_time)
    if end_time:
      self._end_time = datetime.fromisoformat(end_time)

  def Process(self) -> None:
    """Copies logs from an AWS account."""

    output_file = tempfile.NamedTemporaryFile(
    mode='w', delete=False, encoding='utf-8', suffix='.jsonl')
    output_path = output_file.name
    self.logger.info('Downloading logs to {0:s}'.format(output_path))

    # TODO: Add handling for auth related exceptions.
    if self._profile_name:
      session = boto3_session.Session(profile_name=self._profile_name)
    else:
      session = boto3_session.Session()

    cloudtrail_client = session.client('cloudtrail')

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
      # TODO: Add handling for boto3 related exceptions.
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

    self.logger.success('Downloaded logs to {0:s}'.format(output_path))
    output_file.close()

    logs_report = containers.AWSLogs(
        path=output_path, profile_name=self._profile_name,
        query_filter=self._query_filter, start_time=self._start_time,
        end_time=self._end_time)
    self.state.StoreContainer(logs_report)


modules_manager.ModulesManager.RegisterModule(AWSLogsCollector)
