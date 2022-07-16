# -*- coding: utf-8 -*-
"""Helper classes for the GCP cloud resource tree module."""
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Set, Union
from datetime import datetime, timezone
import json
from dateutil import parser

class OperatingMode(Enum):
  """Enum represent operational mode (Online or Offline)."""

  ONLINE = auto()
  OFFLINE = auto()

class LocationType(Enum):
  """Enum represent location type (Zone or Region or Global)."""

  ZONE = auto()
  REGION = auto()
  GLOBAL = auto()


class Resource():
  # pylint: disable=line-too-long
  """A Class that represents a resource (Instance, Disk, Image...etc).

  Attributes:
    id (str): Id of the resource.
    name (str): Name of the resource.
    type (str): Resource type.
    project_id (str): Id of the project where the resource is located.
    location (str): Resource location (zone/region) or 'global'.
    location_type (LocationType): Location type (ZONE/REGION/GLOBAL)
    created_by (str): account that created the resource.
    creator_ip_address (str): IP address of the resource creator at time of
        creation request.
    creator_useragent (str): Useragent of the resource creator at time of
        creation request.
    deleted_by (str): account that deleted the resource.
    deleter_ip_address (str): IP address of the resource deleter at time of
        deletion request.
    deleter_useragent (str): Useragent of the resource deleter at time of
        deletion request.
    parent (Optional[Resource]): Parent resource.
    children (Set[Resource]): Children resources.
    disks (List[Resource]): Disks attached to the resource.
    deleted (bool): Whether the resource is deleted or not.
    _resource_name (str): Full resource name. Maps to protoPayload.resourceName
        in http://cloud/compute/docs/logging/migrating-from-activity-logs-to-audit-logs#fields.
    _creation_timestamp (Optional[datetime]): Resource creation timestamp.
    _deletion_timestamp (Optional[datetime]): Resource deletion timestamp.

  """

  has_dynamic_attributes = True  # silences all attribute-errors for Resource

  def __init__(self) -> None:
    """Initializes the Resource object."""
    self.id: str = str()
    self.name: str = str()
    self.type: str = str()
    self.project_id: str = str()
    self.location: str = str()
    self.location_type: Optional[LocationType] = None
    self.created_by: str = str()
    self.creator_ip_address: str = str()
    self.creator_useragent: str = str()
    self.deleted_by: str = str()
    self.deleter_ip_address: str = str()
    self.deleter_useragent: str = str()
    self.parent: Optional[Resource] = None
    self.children: Set[Resource] = set()
    self.disks: List[Resource] = []
    self.deleted: bool = False
    self._resource_name: str = str()
    self._creation_timestamp: Optional[datetime] = None
    self._deletion_timestamp: Optional[datetime] = None

  def __hash__(self) -> int:
    """For object comparison."""
    return hash(self.id + self.resource_name)

  @property
  def resource_name(self) -> str:
    """Property resource_name Getter."""
    if not self._resource_name and self.name and self.project_id and self.location:
      tmp_type = str()
      if self.type == 'gce_disk':
        tmp_type = 'disks'
      elif self.type == 'gce_instance':
        tmp_type = 'instances'
      elif self.type == 'gce_image':
        tmp_type = 'images'
      elif self.type == 'gce_machine_image':
        tmp_type = 'machineImages'
      elif self.type == 'gce_instance_template':
        tmp_type = 'instanceTemplates'
      elif self.type == 'gce_snapshot':
        tmp_type = 'snapshots'
      else:
        tmp_type = self.type

      if self.location_type == LocationType.GLOBAL:
        return f'projects/{self.project_id}/global/{tmp_type}/{self.name}'
      if self.location_type == LocationType.REGION:
        return f'projects/{self.project_id}/regions/{self.location}/{tmp_type}/{self.name}'  # pylint: disable=line-too-long
      if self.location_type == LocationType.ZONE:
        return f'projects/{self.project_id}/zones/{self.location}/{tmp_type}/{self.name}'  # pylint: disable=line-too-long

    return self._resource_name

  @resource_name.setter
  def resource_name(self, value: str) -> None:
    """Property resource_name Setter.

       This property setter function will split the resource_name and set the
       "type", "location", "project_id" and "name" of the resource.

    Args:
      value: value to set resource_name to.
    """
    # pylint: disable=line-too-long
    # value example:
    # 1- If parsing logs: projects/test-project/zones/us-central1-a/disks/vm1
    # 2- If querying resource through API call: //www.googleapis.com/compute/beta/projects/test-project/zones/us-central1-a/disks/vm1
    # pylint: enable=line-too-long
    if value:
      values = value.split('/')

      self.name = values[-1]

      resource_type = values[-2]
      if resource_type == 'disks':
        self.type = 'gce_disk'
      elif resource_type == 'instances':
        self.type = 'gce_instance'
      elif resource_type == 'images':
        self.type = 'gce_image'
      elif resource_type == 'machineImages':
        self.type = 'gce_machine_image'
      elif resource_type == 'instanceTemplates':
        self.type = 'gce_instance_template'
      elif resource_type == 'snapshots':
        self.type = 'gce_snapshot'
      else:
        self.type = resource_type

      if '/global/' in value:
        self.location = 'global'
        self.location_type = LocationType.GLOBAL
        self.project_id = values[-4]
      else:
        self.location = values[-3]
        self.project_id = values[-5]
        if '/zones/' in value:
          self.location_type = LocationType.ZONE
        elif '/regions/' in value:
          self.location_type = LocationType.REGION

    self._resource_name = value

  @property
  def creation_timestamp(self) -> Optional[datetime]:
    """Property creation_timestamp Getter."""
    return self._creation_timestamp

  @creation_timestamp.setter
  def creation_timestamp(self, value: Union[datetime, str]) -> None:
    """Property creation_timestamp Setter.

    Args:
      value: value to set the creation_timestamp to.
    """
    if isinstance(value, datetime):
      self._creation_timestamp = value
    else:
      self._creation_timestamp = parser.parse(value)

  @property
  def deletion_timestamp(self) -> Optional[datetime]:
    """Property deletion_timestamp Getter."""
    return self._deletion_timestamp

  @deletion_timestamp.setter
  def deletion_timestamp(self, value: Union[datetime, str]) -> None:
    """Property deletion_timestamp Setter.

    Args:
      value: value to set the deletion_timestamp to.
    """
    if isinstance(value, datetime):
      self._deletion_timestamp = value
    else:
      self._deletion_timestamp = parser.parse(value)

  def IsDeleted(self) -> bool:
    """Checks if resource is deleted."""
    if self.deleted or self.deletion_timestamp or not self.creation_timestamp:
      return True

    return False

  def GenerateTree(self) -> List[Dict[str, 'Resource']]:
    """Generates the resource tree.

    Returns:
      List of dictionaries containing a reference to the resource and its name
      indented based on it's location in the tree.
    """
    tab = '\t'
    output: List[Any] = []

    # Count the number of parent resources and the level in the tree the
    # resource is at.
    level = 0
    parent_resource = self.parent
    while parent_resource:
      level = level + 1
      parent_resource = parent_resource.parent

    # Add the resource parent entries to the List of dictionaries
    counter = level
    parent_resource = self.parent
    if parent_resource:
      while counter > 0:
        counter = counter - 1
        entry: Dict[str, Any] = {}
        entry['resource_object'] = parent_resource
        entry['graph'] = f'{tab*counter}|--{parent_resource.name}'
        output.insert(0, entry)
        if parent_resource.parent:
          parent_resource = parent_resource.parent

    # Add resource entry to the List of dictionaries
    entry = {}
    entry['resource_object'] = self
    entry['graph'] = f'{tab*level}|--{self.name}'
    output.insert(level, entry)

    # Add resource children entries to the List of dictionaries
    output.extend(self.GenerateChildrenTree(level + 1))

    return output

  def GenerateChildrenTree(self, level: int) -> List[Dict[str, 'Resource']]:
    """Generates the resource children tree.

    Args:
      level: The level in the tree to place the children at.
    Returns:
      List of dictionaries containing a reference to the children resource and
          their names indented based on their location in the tree.
    """
    result: List[Dict[str, Resource]] = []
    tab = '    '

    for child in self.children:
      entry: Dict[str, Any] = {}
      entry['resource_object'] = child
      entry['graph'] = f'{tab*level}|--{child.name}'
      result.append(entry)

      if child.children:
        result.extend(child.GenerateChildrenTree(level + 1))

    return result

  def __str__(self) -> str:
    """Returns a string representation of the resource tree."""
    output = '\n'
    dashes = '-' * 200
    # pylint: disable=line-too-long
    output_format = '{:<20s}|{:<18s}|{:<20s}|{:<25s}|{:<18s}|{:<20s}|{:<25s}|{:<18s}|{:<100s}\n'

    # Draw table header
    output = output + dashes + '\n'
    output = output + output_format.format(
        'Resource ID', 'Resource Type', 'Creation TimeStamp', 'Created By',
        'Creator IP Addr', 'Deletion Timestamp', 'Deleted By',
        'Deleter IP Addr', 'Tree')
    output = output + dashes + '\n'

    result = self.GenerateTree()
    for i in result:
      resource: Optional[Resource] = i.get('resource_object')
      if resource:
        output = output + \
            (output_format.format( resource.id if ('-' not in resource.id) else "" , resource.type, resource.creation_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if resource.creation_timestamp else "",
            resource.created_by, resource.creator_ip_address,  resource.deletion_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if resource.deletion_timestamp else "", resource.deleted_by, resource.deleter_ip_address,  i.get('graph')))
    output = output + dashes + '\n'

    return output


class ResourceEncoder(json.JSONEncoder):
  """A Class that implements custom json encoding for Resource object."""

  def default(self, o: Resource) -> Dict[str, str]:
    """Returns a dictionary representation of the resource object."""
    if isinstance(o, Resource):
      # pylint: disable=redefined-builtin
      dict = {
          "id": o.id,
          "name": o.name,
          "type": o.type,
          "project_id": o.project_id,
          "location": o.location,
          "created_by": o.created_by,
          "creator_ip_address": o.creator_ip_address,
          "creator_useragent": o.creator_useragent,
          "deleted_by": o.deleted_by,
          "deleter_ip_address": o.deleter_ip_address,
          "deleter_useragent": o.deleter_useragent,
          "resource_name": o.resource_name,
          "creation_timestamp": o.creation_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if o.creation_timestamp else "",  # pylint: disable=line-too-long
          "deletion_timestamp": o.deletion_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if o.deletion_timestamp else ""  # pylint: disable=line-too-long
      }
      return dict

    return super().default(o)
