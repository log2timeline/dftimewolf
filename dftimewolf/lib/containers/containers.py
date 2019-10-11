# -*- coding: utf-8 -*-
"""Attribute container definitions."""

from dftimewolf.lib.containers import interface


class FSPath(interface.AttributeContainer):
  """Filesystem path container.

  Attributes:
    path (str): Filesystem path
  """
  CONTAINER_TYPE = 'fspath'

  def __init__(self, path=None):
    """Initializes the FSPath object.

    Args:
      path (str): Filesystem path
    """
    super(FSPath, self).__init__()
    self.path = path


class RemoteFSPath(FSPath):
  """Remote Filesystem path container.

  Attributes:
    hostname (str): Hostname where the file is located
  """
  CONTAINER_TYPE = 'remotefspath'

  def __init__(self, path=None, hostname=None):
    """Initializes the FSPath object.

    Args:
      path (str): Filesystem path
      hostname (str): Hostname where the file is located
    """
    super(RemoteFSPath, self).__init__(path=path)
    self.hostname = hostname


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


class TicketAttribute(interface.AttributeContainer):
  """Attribute container definition for generic ticketing system attributes.

  Attributes:
    type (str): Type of the attribute.
    name (str): Name of the attribute.
    value (str): Value of the attribute.
  """
  CONTAINER_TYPE = 'ticketattribute'

  def __init__(self, type_, name, value):
    """Initializes the attribute.

    Args:
      type_ (str): Type of the attribute.
      name (str): Name of the attribute.
      value (str): Value of the attribute.
    """
    super(TicketAttribute, self).__init__()
    self.type = type_
    self.name = name
    self.value = value
