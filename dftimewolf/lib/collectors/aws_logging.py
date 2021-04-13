# -*- coding: utf-8 -*-
"""Creates an analysis VM and copies AWS volumes to it for analysis."""

import json
import tempfile

from libcloudforensics.providers.aws.internal import account as aws_account
from libcloudforensics.providers.aws.internal import log as aws_log

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class AWSLogsCollector(module.BaseModule):
  """Collector for Amazon Web Services (AWS) logs."""

  def __init__(self, state, name=None, critical=False):
    """Initializes AWS logs collector."""
    super(AWSLogsCollector, self).__init__(state, name=name, critical=critical)
    self._zone = None
    self._profile_name = None
    self._query_filter = None

  # pylint: disable=arguments-differ
  def SetUp(self, zone, profile_name=None, query_filter=None):
    self._zone = zone
    self._profile_name = profile_name
    self._query_filter = query_filter

  def Process(self):
    """Write me a docstring"""
    output_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, encoding='utf-8', suffix='.jsonl')
    output_path = output_file.name

    log_account = aws_account.AWSAccount(
        self._zone,
        aws_profile=self._profile_name)

    log_client = aws_log.AWSCloudTrail(log_account)

    self.logger.info('Downloading logs to {0:s}'.format(output_path))
    events = log_client.LookupEvents(qfilter='Username,jonathangreig')
    self.logger.info('Downloaded {0:d} log events.'.format(len(events)))

    # Set the default serializer to str() to account for datetime objects.
    output_file.write(json.dumps(events, default=str))
    output_file.write('\n')
    self.logger.info('Downloaded logs to {0:s}'.format(output_path))
    output_file.close()


modules_manager.ModulesManager.RegisterModule(AWSLogsCollector)
