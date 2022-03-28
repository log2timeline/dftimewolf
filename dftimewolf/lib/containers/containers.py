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
      attributes: Optional[List[Dict[str, Any]]] = None) -> None:
    """Initializes the analysis report.

    Args:
      module_name (str): name of the module that generated the report.
      text (str): report text.
      text_format (str): format of text in the report. Must be either
        'plaintext' or 'markdown'.
      attributes (list): attribute list of dicts that must contain 'name',
        'type', 'values' keys.
    """
    super(Report, self).__init__(attributes=attributes)
    self.module_name = module_name
    self.text = text
    self.text_format = text_format


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


class YaraRule(interface.AttributeContainer):
  """Attribute container representing Yara rules.

  Attributes:
    name: The name of the Yara rule.
    rule_text: The actual Yara rule string.
  """
  def __init__(self, name: str, rule_text: str) -> None:
    super(YaraRule, self).__init__()
    self.name = name
    self.rule_text = rule_text


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


class GCEDisk(interface.AttributeContainer):
  """Attribute container definition for a GCE Disk object.

  Attributes:
    name (str): The disk name.
  """
  CONTAINER_TYPE = 'gcedisk'

  def __init__(self, name: str) -> None:
    super(GCEDisk, self).__init__()
    self.name = name

  def __eq__(self, other: GCEDisk) -> bool:
    """Override __eq__() for this container."""
    return self.name == other.name

class GCEDiskEvidence(interface.AttributeContainer):
  """Attribute container definition for a GCE Disk that has been copied.

  Attributes:
    name (str): The disk name.
    project (str): The project the disk was copied to.
  """
  CONTAINER_TYPE = 'gcediskevidence'

  def __init__(self, name: str, project: str) -> None:
    super(GCEDiskEvidence, self).__init__()
    self.name = name
    self.project = project


class GCEImage(interface.AttributeContainer):
  """Attribute container definition for a GCE Image object.

  Attributes:
    name (str): The image name.
  """
  CONTAINER_TYPE = 'gceimage'

  def __init__(self, name: str) -> None:
    super(GCEImage, self).__init__()
    self.name = name


class DataFrame(interface.AttributeContainer):
  """Attribute container definition for a Pandas DataFrame.

  Attributes:
    data_frame (pandas.DataFrame): DataFrame containing the data.
    description (str): Description of the data in the data frame.
    name (str): Name of the data frame.
    source (str): The source of the data in the DataFrame.
  """

  CONTAINER_TYPE = 'data_frame'

  def __init__(
      self,
      data_frame: "pandas.DataFrame",
      description: str,
      name: str,
      source: Optional[str] = None) -> None:
    super(DataFrame, self).__init__()
    self.data_frame = data_frame
    self.description = description
    self.name = name
    self.source = source


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
      user_key: Optional[str ]= '',
      start_time: Optional[str]='',
      end_time: Optional[str]='') -> None:
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


class AWSVolume(interface.AttributeContainer):
  """Attribute container for an AWS Volume.

  Attributes:
    vol_id (str): The volume id (vol-xxxxxxxx)."""

  CONTAINER_TYPE = 'aws_volume'

  def __init__(self, vol_id: str) -> None:
    super(AWSVolume, self).__init__()
    self.id = vol_id


class AWSSnapshot(interface.AttributeContainer):
  """Attribute container for an AWS Snapshot.

  Attributes:
    snap_id (str): The snapshot id (snap-xxxxxxxx)."""

  CONTAINER_TYPE = 'aws_snapshot'

  def __init__(self, snap_id: str) -> None:
    super(AWSSnapshot, self).__init__()
    self.id = snap_id


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
