# -*- coding: utf-8 -*-
"""Attribute container definitions."""

from dftimewolf.lib.containers import interface


class Report(interface.AttributeContainer):
  """Analysis report attribute container.

  Attributes:
    module_name (str): name of the module that generated the report.
    text (str): report text.
    text_format (str): format of text in the report. Must be either 'plaintext'
      or 'markdown'
    attributes (list): attribute list, dicts must contain 'name',
      'type', 'values' keys.
  """
  CONTAINER_TYPE = 'report'

  def __init__(
      self, module_name, text, text_format='plaintext', attributes=None):
    """Initializes the analysis report.

    Args:
      module_name (str): name of the analysis plugin that generated
          the report.
      text (str): report text.
      text_format (str): format of text in the report. Must be either
        'plaintext' or 'markdown'.
      attributes (list): attribute list of dicts that must contain 'name',
        'type', 'values' keys.
    """
    super(Report, self).__init__()
    self.module_name = module_name
    self.text = text
    self.text_format = text_format
    if attributes is None:
      self.attributes = []
    else:
      self.attributes = attributes


class StackdriverLogs(interface.AttributeContainer):
  """Analysis report attribute container.

  Attributes:
    filter_expression (str): Stackdriver advanced logs filter expression
        used to generate the results.
    path (str): path to a stackdriver log file.
    project_name (str): name of the project that was queried.
  """
  CONTAINER_TYPE = 'stackdriver_logs'

  def __init__(self, path, filter_expression, project_name):
    """Initializes the analysis report.

    Args:
      filter_expression (str): Stackdriver advanced logs filter expression
          used to generate the results.
      path (str): path to a stackdriver log file.
      project_name (str): name of the project that was queried.
    """
    super(StackdriverLogs, self).__init__()
    self.filter_expression = filter_expression
    self.path = path
    self.project_name = project_name


class ThreatIntelligence(interface.AttributeContainer):
  """Threat Intelligence attribute container.

  Attributes:
    name (string): name of the threat
    indicator (string): regular expression relevant to a threat
  """
  CONTAINER_TYPE = 'threat_intelligence'

  def __init__(self, name, indicator):
    """Initializes the Threat Intelligence container.

    Args:
      name (string): name of the threat
      indicator (string): regular expression relevant to a threat
    """
    super(ThreatIntelligence, self).__init__()
    self.name = name
    self.indicator = indicator
