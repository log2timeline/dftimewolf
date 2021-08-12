# -*- coding: utf-8 -*-
"""Attribute container definitions."""

from datetime import datetime
from typing import Optional, Union, List, TYPE_CHECKING, Dict, Any

from dftimewolf.lib.containers import interface

if TYPE_CHECKING:
  from libcloudforensics.providers.aws.internal.ebs import AWSVolume
  from libcloudforensics.providers.azure.internal.compute import AZComputeDisk
  from libcloudforensics.providers.gcp.internal.compute import GoogleComputeDisk
  import pandas


class FSPath(interface.AttributeContainer):
  """Filesystem path container.

  Attributes:
    path (str): Filesystem path.
  """
  CONTAINER_TYPE = 'fspath'

  def __init__(self, path: str) -> None:
    """Initializes the FSPath object.

    Args:
      path (str): Filesystem path
    """
    super(FSPath, self).__init__()
    self.path = path


class RemoteFSPath(FSPath):
  """Remote Filesystem path container.

  Attributes:
    hostname (str): Hostname where the file is located.
    path (str): Filesystem path.
  """
  CONTAINER_TYPE = 'remotefspath'

  def __init__(self,
               path: str,
               hostname: str) -> None:
    """Initializes the FSPath object.

    Args:
      path (str): Filesystem path
      hostname (str): Hostname where the file is located
    """
    super(RemoteFSPath, self).__init__(path=path)
    self.hostname = hostname


class Report(interface.AttributeContainer):
  """Report attribute container.

  Attributes:
    module_name (str): name of the module that generated the report.
    text (str): report text.
    text_format (str): format of text in the report. Must be either 'plaintext'
      or 'markdown'.
    attributes (list): attribute list, dicts must contain 'name',
      'type', 'values' keys.
  """
  CONTAINER_TYPE = 'report'

  def __init__(
      self,
      module_name: str,
      text: str,
      text_format: str='plaintext',
      attributes: Optional[List[Dict[str, Any]]]=None) -> None:
    """Initializes the analysis report.

    Args:
      module_name (str): name of the module that generated the report.
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


class GCPLogs(interface.AttributeContainer):
  """Google Cloud Platform logs container.

  Attributes:
    filter_expression (str): GCP logging advanced logs filter expression
        used to generate the results.
    path (str): path to a GCP log file.
    project_name (str): name of the project that was queried.
  """
  CONTAINER_TYPE = 'gcp_logs'

  def __init__(self, path: str, filter_expression: str, project_name: str):
    """Initializes the GCP logs container.

    Args:
      filter_expression (str): GCP advanced logs filter expression
          used to generate the results.
      path (str): path to a GCP log file.
      project_name (str): name of the project that was queried.
    """
    super(GCPLogs, self).__init__()
    self.filter_expression = filter_expression
    self.path = path
    self.project_name = project_name


class AWSLogs(interface.AttributeContainer):
  """AWS logs container.

  Attributes:
      path (str): path to a AWS log file.
      profile_name (str): the profile used to collect logs.
      query_filter (str): the query filter used in the log query.
      start_time (str): the start time used in the log query in format
        'YYYY-MM-DD HH:MM:SS.US'.
      end_time (str): the end time used in the log query in format
        'YYYY-MM-DD HH:MM:SS.US'.
  """
  CONTAINER_TYPE = 'aws_logs'

  def __init__(self,
               path: str,
               profile_name: Optional[str],
               query_filter: Optional[str],
               start_time: Optional[datetime],
               end_time: Optional[datetime]) -> None:
    """Initializes the AWS logs container.

    Args:
      path (str): path to a AWS log file.
      profile_name (str): the profile used to collect logs.
      query_filter (str): the query filter used in the log query.
      start_time (datetime): the start time used in the log query.
      end_time (datetime): the end time used in the log query.
    """
    super(AWSLogs, self).__init__()
    self.path = path
    self.profile_name = profile_name
    self.query_filter = query_filter
    self.start_time = str(start_time)
    self.end_time = str(end_time)


class ThreatIntelligence(interface.AttributeContainer):
  """Threat Intelligence attribute container.

  Attributes:
    name (string): name of the threat.
    indicator (string): regular expression relevant to a threat.
    path (string): path to the indicator data (e.g. file).
  """
  CONTAINER_TYPE = 'threat_intelligence'

  def __init__(self, name: str, indicator: Optional[str], path: str) -> None:
    """Initializes the Threat Intelligence container.

    Args:
      name (string): name of the threat.
      indicator (string): regular expression relevant to a threat.
      path (string): path to the indicator data (e.g. file)
    """
    super(ThreatIntelligence, self).__init__()
    self.name = name
    self.indicator = indicator
    self.path = path

class TicketAttribute(interface.AttributeContainer):
  """Attribute container definition for generic ticketing system attributes.

  Attributes:
    type (str): Type of the attribute.
    name (str): Name of the attribute.
    value (str): Value of the attribute.
  """
  CONTAINER_TYPE = 'ticketattribute'

  def __init__(self, type_: str, name: str, value: str) -> None:
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


class File(interface.AttributeContainer):
  """Attribute container definition for generic files.

  Attributes:
    name (str): Human-friendly name or short description of the file.
    path (str): Full path to the file.
    description (str): Longer description of the file.
  """
  CONTAINER_TYPE = 'file'

  def __init__(self,
               name: str,
               path: str,
               description: Optional[str]=None) -> None:
    """Initializes the attribute.

    Args:
      name (str): Human-friendly name or short description of the file.
      path (str): Full path to the file.
      description (Optional[str]): Longer description of the file.
    """
    super(File, self).__init__()
    self.name = name
    self.path = path
    self.description = description

class ForensicsVM(interface.AttributeContainer):
  """Attribute container definition for a forensics virtual machine.

  Attributes:
    name (str): Identifying name for the virtual machine.
    evidence_disk (libcloudforensics.GoogleComputeDisk): The disk containing
        the forensic evidence. Full definition in
        libcloudforensics.providers.gcp.internal.GoogleComputeDisk.
    platform (str): The cloud platform where the VM is located. One of
        {gcp,aws,azure}.
  """
  CONTAINER_TYPE = 'forensics_vm'

  def __init__(self,
               name: str,
               evidence_disk: Union["GoogleComputeDisk",
                                    "AWSVolume",
                                    "AZComputeDisk"],
               platform: str) -> None:
    super(ForensicsVM, self).__init__()
    self.name = name
    self.evidence_disk = evidence_disk
    self.platform = platform


class URL(interface.AttributeContainer):
  """Attribute container definition for a Uniform Resource Locator.

  Attributes:
    path (str): The full path to the URL.
  """
  CONTAINER_TYPE = 'url'

  def __init__(self, path: str) -> None:
    super(URL, self).__init__()
    self.path = path


class DataFrame(interface.AttributeContainer):
  """Attribute container definition for a Pandas DataFrame.

  Attributes:
    data_frame (pandas.DataFrame): DataFrame containing the data.
    description (str): Description of the data in the data frame.
    name (str): Name of the data frame.
  """

  CONTAINER_TYPE = 'data_frame'

  def __init__(
      self, data_frame: "pandas.DataFrame", description: str, name: str):
    super(DataFrame, self).__init__()
    self.data_frame = data_frame
    self.description = description
    self.name = name


class Host(interface.AttributeContainer):
  """Attribute container definition for a host.

  Attributes:
    hostname (str): The host's hostname.
    platform (str): The host's platform. One of {win, linux, macos, unknown}.
  """

  CONTAINER_TYPE = 'host'

  def __init__(self, hostname: str, platform: str='unknown') -> None:
    super(Host, self).__init__()
    self.hostname = hostname
    self.platform = platform


class WorkspaceLogs(interface.AttributeContainer):
  """Google Workspace logs container.

  Attributes:
    application_name (str): Name of the application the audit records are for
    filter_expression (str): Workspace audit logs filter expression
          used to generate the results.
    path (str): path to a Workspace log file.
  """
  CONTAINER_TYPE = 'workspace_logs'

  def __init__(self, application_name: str, path: str, filter_expression: str):
    """Initializes the Workspace logs container.

    Args:
      application_name (str): Name of the application the audit records are for
      filter_expression (str): Workspace audit logs filter expression
          used to generate the results.
      path (str): path to a Workspace log file.
    """
    super(WorkspaceLogs, self).__init__()
    self.filter_expression = filter_expression
    self.path = path
    self.application_name = application_name
