# -*- coding: utf-8 -*-
"""Creates an analysis VM and copies AWS volumes to it for analysis."""

from libcloudforensics.providers.aws.internal import account as aws_account
from libcloudforensics.providers.aws.internal import AWSCloudTrail

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager


class AWSLogsCollector(module.BaseModule):
  """Collector for Amazon Web Services (AWS) logs."""

  def __init__(self, state, name=None, critical=False):
    """Initializes AWS logs collector."""
    super(AWSLogsCollector, self).__init__(state, name=name, critical=critical)


  def SetUp(self):
      pass

  def Process(self):
    pass


modules_manager.ModulesManager.RegisterModule(AWSLogsCollector)
