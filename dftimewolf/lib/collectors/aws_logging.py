# -*- coding: utf-8 -*-
"""Reads logs from an AWS account"""

import json
import tempfile
from datetime import datetime

from libcloudforensics.providers.aws.internal import account as aws_account
from libcloudforensics.providers.aws.internal import log as aws_log

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager


class AWSLogsCollector(module.BaseModule):
  """Collector for Amazon Web Services (AWS) logs."""

  def __init__(self, state, name=None, critical=False):
    """Initializes AWS logs collector."""
    super(AWSLogsCollector, self).__init__(state, name=name, critical=critical)
    self._zone = None
    self._profile_name = None
    self._query_filter = None
    self._start_time = None
    self._end_time = None

  # pylint: disable=arguments-differ
  def SetUp(self, zone, profile_name=None, query_filter=None,
    start_time=None, end_time=None):
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

  def Process(self):
    """Copies logs from an AWS account."""

    output_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, encoding='utf-8', suffix='.jsonl')
    output_path = output_file.name
    log_account = aws_account.AWSAccount(
        self._zone, aws_profile=self._profile_name)
    log_client = aws_log.AWSCloudTrail(log_account)

    self.logger.info('Downloading logs to {0:s}'.format(output_path))
    events = log_client.LookupEvents(qfilter=self._query_filter,
        starttime=self._start_time, endtime=self._end_time)
    self.logger.info('Downloaded {0:d} log events.'.format(len(events)))

    # Set the default serializer to str() to account for datetime objects.
    output_file.write(json.dumps(events, default=str))
    output_file.write('\n')
    self.logger.info('Downloaded logs to {0:s}'.format(output_path))
    output_file.close()

    logs_report = containers.AWSLogs(
        path=output_path, profile_name=self._profile_name,
        query_filter=self._query_filter, start_time=self._start_time,
        end_time=self._end_time)
    self.state.StoreContainer(logs_report)


modules_manager.ModulesManager.RegisterModule(AWSLogsCollector)
