# -*- coding: utf-8 -*-
"""Attribute container definitions."""

from __future__ import annotations

from typing import Optional, Union, List, TYPE_CHECKING, Dict, Any

from dftimewolf.lib.containers import interface

if TYPE_CHECKING:
  from libcloudforensics.providers.aws.internal.ebs import AWSVolume as AWSVol
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

  def __str__(self) -> str:
    """Override __str()__."""
    return self.path


class RemoteFSPath(FSPath):
  """Remote Filesystem path container.

  Attributes:
    hostname (str): Hostname where the file is located.
    path (str): Filesystem path.
  """
  CONTAINER_TYPE = 'remotefspath'

  def __init__(self, path: str, hostname: str) -> None:
    """Initializes the FSPath object.

    Args:
      path (str): Filesystem path
      hostname (str): Hostname where the file is located
    """
    super(RemoteFSPath, self).__init__(path=path)
    self.hostname = hostname

  def __str__(self) -> str:
    """Override __str()__."""
    return f'{self.hostname}:{self.path}'


class Report(interface.AttributeContainer):
  """Report attribute container.

  Attributes:
    module_name (str): name of the module that generated the report.
    text (str): report text.
    text_format (str): format of text in the report. Must be either 'plaintext'
      or 'markdown'.
  """
  CONTAINER_TYPE = 'report'

  def __init__(
      self,
      module_name: str,
      text: str,
      text_format: str = 'plaintext',
      metadata: Optional[Dict[str, Any]] = None) -> None:
    """Initializes the analysis report.

    Args:
      module_name (str): name of the module that generated the report.
      text (str): report text.
      text_format (str): format of text in the report. Must be either
        'plaintext' or 'markdown'.
      metadata (dict): a dict for optional report metadata to be used by
        exporter modules.
    """
    super(Report, self).__init__(metadata=metadata)
    self.module_name = module_name
    self.text = text
    self.text_format = text_format

  def __str__(self) -> str:
    """Override __str()__."""
    return f'{self.module_name} Report'


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

  def __str__(self) -> str:
    """Override __str()__."""
    return f'{self.project_name}:{self.path}'


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

  def __str__(self) -> str:
    """Override __str()__."""
    return f'{self.name}:{self.indicator}:{self.path}'


class YaraRule(interface.AttributeContainer):
  """Attribute container representing Yara rules.

  Attributes:
    name: The name of the Yara rule.
    rule_text: The actual Yara rule string.
  """
  CONTAINER_TYPE = 'yara_rule'

  def __init__(self, name: str, rule_text: str) -> None:
    super(YaraRule, self).__init__()
    self.name = name
    self.rule_text = rule_text

  def __str__(self) -> str:
    """Override __str()__."""
    return self.name


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

  def __eq__(self, other: 'TicketAttribute') -> bool:
    """Override '==' operator. Used only in unit tests."""
    return (
        self.type == other.type and self.name == other.name and
        self.value == other.value)

  def __str__(self) -> str:
    """Override __str()__."""
    return self.name


class File(interface.AttributeContainer):
  """Attribute container definition for generic files.

  Attributes:
    name (str): Human-friendly name or short description of the file.
    path (str): Full path to the file.
    description (str): Longer description of the file.
  """
  CONTAINER_TYPE = 'file'

  def __init__(
      self, name: str, path: str, description: Optional[str] = None) -> None:
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

  def __str__(self) -> str:
    """Override __str()__."""
    if self.path.endswith(self.name):
      return self.path
    return f'{self.path}/{self.name}'

  def __eq__(self, other: File) -> bool:
    """Override __eq__() for this container."""
    return self.name == other.name and self.path == other.path


class Directory(interface.AttributeContainer):
  """Attribute container definition for generic directories.

  Attributes:
    name (str): Human-friendly name or short description of the directory.
    path (str): Full path to the directory.
    description (str): Longer description of the directory.
  """
  CONTAINER_TYPE = 'directory'

  def __init__(
      self, name: str, path: str, description: Optional[str] = None) -> None:
    """Initializes the attribute.

    Args:
      name (str): Human-friendly name or short description of the file.
      path (str): Full path to the file.
      description (Optional[str]): Longer description of the file.
    """
    super(Directory, self).__init__()
    self.name = name
    self.path = path
    self.description = description

  def __str__(self) -> str:
    """Override __str()__."""
    return self.path


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

  def __init__(
      self, name: str, evidence_disk: Union["GoogleComputeDisk", "AWSVol",
                                            "AZComputeDisk", None],
      platform: str) -> None:
    super(ForensicsVM, self).__init__()
    self.name = name
    self.evidence_disk = evidence_disk
    self.platform = platform

  def __str__(self) -> str:
    """Override __str()__."""
    return self.name


class URL(interface.AttributeContainer):
  """Attribute container definition for a Uniform Resource Locator.

  Attributes:
    path (str): The full path to the URL.
  """
  CONTAINER_TYPE = 'url'

  def __init__(self, path: str) -> None:
    super(URL, self).__init__()
    self.path = path

  def __str__(self) -> str:
    """Override __str()__."""
    return self.path


class GCEDisk(interface.AttributeContainer):
  """Attribute container definition for a GCE Disk object.

  Attributes:
    name (str): The disk name.
    project (str): The project the disk lives in.
  """
  CONTAINER_TYPE = 'gcedisk'

  def __init__(self, name: str, project: str) -> None:
    super(GCEDisk, self).__init__()
    self.name = name
    self.project = project

  def __eq__(self, other: GCEDisk) -> bool:
    """Override __eq__() for this container."""
    return self.name == other.name and self.project == other.project

  def __str__(self) -> str:
    """Override __str()__."""
    return f'{self.project}:{self.name}'


class GCEImage(interface.AttributeContainer):
  """Attribute container definition for a GCE Image object.

  Attributes:
    name (str): The image name.
  """
  CONTAINER_TYPE = 'gceimage'

  def __init__(self, name: str, project: str) -> None:
    super(GCEImage, self).__init__()
    self.name = name
    self.project = project

  def __str__(self) -> str:
    """Override __str()__."""
    return f'{self.project}:{self.name}'


class DataFrame(interface.AttributeContainer):
  """Attribute container definition for a Pandas DataFrame.

  Attributes:
    data_frame (pandas.DataFrame): DataFrame containing the data.
    description (str): Description of the data in the data frame.
    name (str): Name of the data frame.
    source (str): The source of the data in the DataFrame.
    metadata (dict): a dict for optional report metadata to be used by
        exporter modules.
  """

  CONTAINER_TYPE = 'data_frame'

  def __init__(
      self,
      data_frame: "pandas.DataFrame",
      description: str,
      name: str,
      source: Optional[str] = None,
      metadata: Optional[Dict[str, Any]] = None) -> None:
    super(DataFrame, self).__init__(metadata=metadata)
    self.data_frame = data_frame
    self.description = description
    self.name = name
    self.source = source

  def __str__(self) -> str:
    """Override __str()__."""
    return self.name


class Host(interface.AttributeContainer):
  """Attribute container definition for a host.

  Attributes:
    hostname (str): The host's hostname.
    platform (str): The host's platform. One of {win, linux, macos, unknown}.
  """

  CONTAINER_TYPE = 'host'

  def __init__(self, hostname: str, platform: str = 'unknown') -> None:
    super(Host, self).__init__()
    self.hostname = hostname
    self.platform = platform

  def __str__(self) -> str:
    """Override __str()__."""
    return self.hostname

  def __eq__(self, other: Host) -> bool:
    """Override __eq__() for this container."""
    return self.hostname == other.hostname and self.platform == other.platform


class GrrFlow(interface.AttributeContainer):
  """Attribute container definition for a host.

  Attributes:
    hostname (str): The host's hostname.
    flow_id (str): A hexadecimal flow ID.
  """

  CONTAINER_TYPE = 'grr_flow'

  def __init__(self, hostname: str, flow: str) -> None:
    super(GrrFlow, self).__init__()
    self.hostname = hostname
    self.flow_id = flow

  def __str__(self) -> str:
    """Override __str()__."""
    return f'{self.hostname}:{self.flow_id}'

  def __eq__(self, other: GrrFlow) -> bool:
    """Override __eq__() for this container."""
    return self.hostname == other.hostname and self.flow_id == other.flow_id


class WorkspaceLogs(interface.AttributeContainer):
  """Google Workspace logs container.

  Attributes:
    application_name (str): Name of the application the audit records are for
    filter_expression (str): Workspace audit logs filter expression
        used to generate the results.
    path (str): path to a Workspace log file.
    user_key (str): user key associated with the audit records.
    start_time (Optional[str]): Beginning of the time period the results cover.
    end_time (Optional[str]): End of the time period the results cover.
  """
  CONTAINER_TYPE = 'workspace_logs'

  def __init__(
      self,
      application_name: str,
      path: str,
      filter_expression: str,
      user_key: Optional[str] = '',
      start_time: Optional[str] = '',
      end_time: Optional[str] = '') -> None:
    """Initializes the Workspace logs container.

    Args:
      application_name (str): Name of the application the audit records are for.
      path (str): path to a Workspace log file.
      filter_expression (str): Workspace audit logs filter expression
          used to generate the results.
      user_key (Optional[str]): user key associated with the audit records.
      start_time (Optional[str]): Beginning of the time period the results
          cover. Format yyyy-mm-ddTHH:MM:SSZ.
      end_time (Optional[str]): End of the time period the results cover. Format
          yyyy-mm-ddTHH:MM:SSZ.
    """
    super(WorkspaceLogs, self).__init__()
    self.filter_expression = filter_expression
    self.path = path
    self.application_name = application_name
    self.user_key = user_key
    self.start_time = start_time
    self.end_time = end_time

  def __str__(self) -> str:
    """Override __str()__."""
    return f'{self.application_name}:{self.path}'


class GCSObject(interface.AttributeContainer):
  """GCS Objects container.

  Attributes:
    path (str): GCS object path.
  """
  CONTAINER_TYPE = 'gcs_object'

  def __init__(self, path: str):
    """Initializes the GCS object container.

    Args:
      path (str): GCS object paths.
    """
    super(GCSObject, self).__init__()
    if path.startswith('gs://'):
      self.path = path
    else:
      self.path = 'gs://' + path

  def __str__(self) -> str:
    """Override __str()__."""
    return self.path


class AWSS3Object(interface.AttributeContainer):
  """S3 Object container.

  Attributes:
    path (str): S3 Object path.
  """

  CONTAINER_TYPE = 'aws_s3_object'

  def __init__(self, path: str):
    """Initialise an S3Image object.

    Args:
      path (str): S3 object path.
    """
    super(AWSS3Object, self).__init__()
    if path.startswith('s3://'):
      self.path = path
    else:
      self.path = 's3://' + path

  def __str__(self) -> str:
    """Override __str()__."""
    return self.path


class AWSVolume(interface.AttributeContainer):
  """Attribute container for an AWS Volume.

  Attributes:
    vol_id (str): The volume id (vol-xxxxxxxx)."""

  CONTAINER_TYPE = 'aws_volume'

  def __init__(self, vol_id: str) -> None:
    super(AWSVolume, self).__init__()
    self.id = vol_id

  def __str__(self) -> str:
    """Override __str()__."""
    return self.id


class AWSSnapshot(interface.AttributeContainer):
  """Attribute container for an AWS Snapshot.

  Attributes:
    snap_id (str): The snapshot id (snap-xxxxxxxx)."""

  CONTAINER_TYPE = 'aws_snapshot'

  def __init__(self, snap_id: str) -> None:
    super(AWSSnapshot, self).__init__()
    self.id = snap_id

  def __str__(self) -> str:
    """Override __str()__."""
    return self.id


class OsqueryQuery(interface.AttributeContainer):
  """Attribute container for an Osquery query.

  Attributes:
    query (str): The osquery query.
    name (Optional[str]): A name for the osquery.
    platforms (Optional[List[str]]): A constraint on the platform(s) the query
        should be run.  Valid values are 'darwin', 'linux', 'windows',
    description (Optional[str]): A description for the query.
  """

  CONTAINER_TYPE = 'osquery_query'

  def __init__(
      self,
      query: str,
      name: Optional[str] = None,
      platforms: Optional[List[str]] = None,
      description: Optional[str] = None) -> None:
    super(OsqueryQuery, self).__init__()
    self.description = description
    self.name = name
    self.platforms = platforms
    self.query = query

  def __str__(self) -> str:
    """Override __str()__."""
    return f'{self.name}'


class OsqueryResult(interface.AttributeContainer):
  """Attribute container for an Osquery result.

  Attributes:
    name (str): Name for the osquery.
    description (str): A description for the query.
    query (str): The osquery query.
    hostname (str): The hostname.
    data_frame (pandas.DataFrame): A dataframe containing the result.
    flow_identifier (Optional[str]): The source GRR Flow Identifier.
    client_identifier (Optional[str]): The source GRR client identifier.
  """

  CONTAINER_TYPE = 'osquery_result'

  def __init__(
      self,
      data_frame: pandas.DataFrame,
      hostname: str,
      query: str,
      client_identifier: Optional[str] = None,
      description: Optional[str] = None,
      flow_identifier: Optional[str] = None,
      name: Optional[str] = None) -> None:
    super(OsqueryResult, self).__init__()
    self.data_frame = data_frame
    self.hostname = hostname
    self.query = query
    self.client_identifier = client_identifier
    self.description = description
    self.flow_identifier = flow_identifier
    self.name = name

  def __eq__(self, other: OsqueryResult) -> bool:
    """Override __eq__() for this container."""
    return self.hostname == other.hostname and self.query == other.query

  def __str__(self) -> str:
    """Override __str()__."""
    return f'{self.hostname}:{self.name}'


class BigQueryQuery(interface.AttributeContainer):
  """Attribute container for a BigQuery query.

  Attributes:
    query: The query string
    description: A description of the query
    pandas_output: True if results should be kept in a dataframe, false to write
        to disk.
  """

  CONTAINER_TYPE = 'bigquery_query'

  def __init__(self, query: str, description: str, pandas_output: bool) -> None:
    super(BigQueryQuery, self).__init__()
    self.query = query
    self.description = description
    self.pandas_output = pandas_output

  def __eq__(self, other: BigQueryQuery) -> bool:
    """Override __eq__() for this container."""
    return self.query == other.query

  def __str__(self) -> str:
    """Override __str()__."""
    return self.description


class SQLQuery(interface.AttributeContainer):
  """SQL Query container.

  Attributes:
    query: The SQL query string.
    description: A description of the query.
  """

  CONTAINER_TYPE = "sql_query"

  def __init__(self, query: str, description: str) -> None:
    super().__init__()
    self.query = query
    self.description = description

  def __str__(self) -> str:
    """Override __str()__."""
    return self.description

  def __eq__(self, other: SQLQuery) -> bool:
    """Override __eq__() for this container."""
    return self.query == other.query


class Telemetry(interface.AttributeContainer):
  """Attribute container for Telemetry.

  Attributes:
    key: The key of the telemetry.
    value: The value of the telemetry.
  """

  CONTAINER_TYPE = 'telemetry'

  def __init__(self, key: str, value: str):
    super(Telemetry, self).__init__()
    self.key = key
    self.value = value

  def __str__(self) -> str:
    """Override __str()__."""
    return f'Telemetry<{self.key}:{self.value}>'


class TurbiniaRequest(interface.AttributeContainer):
  """Turbinia request container.

  Attributes:
    project (str): name of the GCP project containing the disk to process.
    request_id (str): Turbinia request identifier.
    evidence_name (str): Name of the evidence being processed.
  """
  CONTAINER_TYPE = 'turbiniarequest'

  def __init__(
      self,
      project: str,
      request_id: Optional[str] = None,
      evidence_name: Optional[str] = None) -> None:
    """Initializes the Turbinia-request attribute container.

    Args:
      project (str): name of the GCP project containing the disk to process.
      request_id: Turbinia request identifier.
      evidence_name: Name of the evidence being processed.
    """
    super().__init__()
    self.request_id = request_id
    self.evidence_name = evidence_name
    self.project = project

  def __str__(self) -> Optional[str]:
    """Overrides __str()__."""
    return self.request_id if self.request_id else self.evidence_name

  def __eq__(self, other: TurbiniaRequest) -> bool:
    """Override __eq__() for this container."""
    return self.request_id == other.request_id


class GRRArtifact(interface.AttributeContainer):
  """GRR Artifact container.

  Attributes:
    name: Name of the GRR artifact.
  """

  CONTAINER_TYPE = "grr_artifact"

  def __init__(self, name: str):
    super().__init__()
    self.name = name

  def __str__(self) -> str:
    """Override __str()__."""
    return self.name

  def __eq__(self, other: GRRArtifact) -> bool:
    """Override __eq__() for this container."""
    return self.name == other.name
