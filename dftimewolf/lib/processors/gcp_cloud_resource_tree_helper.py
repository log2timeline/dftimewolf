# -*- coding: utf-8 -*-
"""Helper classes for the GCP cloud resource tree module."""
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Set, Union
from datetime import datetime, timezone
from dateutil import parser


class OperatingMode(Enum):
  """Enum represent operational mode (Online or Offline)."""

  ONLINE = auto()
  OFFLINE = auto()


class Resource:
  """A Class that represents a resource (Instance, Disk, Image...etc).

  Attributes:
    id (str): Id of the resource.
    name (str): Name of the resource.
    type (str): Resource type.
    project_id (str): Id of the project where the resource is located.
    zone (str): Zone where the resource is located.
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
    in
    http://cloud/compute/docs/logging/migrating-from-activity-logs-to-audit-logs#fields.     # pylint: disable=line-too-long
    _creation_timestamp (Optional[datetime]): Resource creation timestamp.
    _deletion_timestamp (Optional[datetime]): Resource deletion timestamp.

  """

  has_dynamic_attributes = True  # silences all attribute-errors for Resource

  def __init__(self) -> None:
    """Initializes the Resource object."""
    self.id: str = ''
    self.name: str = ''
    self.type: str = ''
    self.project_id: str = ''
    self.zone: str = ''
    self.created_by: str = ''
    self.creator_ip_address: str = ''
    self.creator_useragent: str = ''
    self.deleted_by: str = ''
    self.deleter_ip_address: str = ''
    self.deleter_useragent: str = ''
    self.parent: Optional[Resource] = None
    self.children: Set[Resource] = set()
    self.disks: List[Resource] = []
    self.deleted: bool = False
    self._resource_name: str = ''
    self._creation_timestamp: Optional[datetime] = None
    self._deletion_timestamp: Optional[datetime] = None

  def __hash__(self) -> int:
    """For object comparison."""
    return hash(self.id + self.resource_name)

  @property
  def resource_name(self) -> str:
    """Property resource_name Getter."""
    return self._resource_name

  @resource_name.setter
  def resource_name(self, value: str) -> None:
    """Property resource_name Setter.

       This property setter function will split the resource_name and set the
       "type", "zone", "project_id" and "name" of the resource.

    Args:
      value: value to set resource_name to.
    """
    # pylint: disable=line-too-long
    # value example:
    # 1- If parsing logs: projects/test-project-hkhalifa/zones/us-central1-a/disks/vm1
    # 2- If querying resource through API call: //www.googleapis.com/compute/beta/projects/test-project-hkhalifa/zones/us-central1-a/disks/vm1
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

      if '/zones/' in value:
        self.zone = values[-3]
        self.project_id = values[-5]
      elif '/global/' in value:
        self.zone = 'global'
        self.project_id = values[-4]

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

    # Draw table header
    output = output + dashes + '\n'
    # pylint: disable=line-too-long
    output = output + '{:<20s}|{:<18s}|{:<20s}|{:<25s}|{:<18s}|{:<20s}|{:<25s}|{:<18s}|{:<100s}\n'.format(
        'Resource ID', 'Resource Type', 'Creation TimeStamp', 'Created By',
        'Creator IP Addr', 'Deletion Timestamp', 'Deleted By',
        'Deleter IP Addr', 'Tree')
    output = output + dashes + '\n'

    result = self.GenerateTree()
    for i in result:
      resource: Optional[Resource] = i.get('resource_object')
      if resource:
        output = output + \
            ('{:<20s}|{:<18s}|{:<20s}|{:<25s}|{:<18s}|{:<20s}|{:<25s}|{:<18s}|{:<100s}\n'.format( resource.id if ('-' not in resource.id) else "" , resource.type, resource.creation_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if resource.creation_timestamp else "",
            resource.created_by, resource.creator_ip_address,  resource.deletion_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if resource.deletion_timestamp else "", resource.deleted_by, resource.deleter_ip_address,  i.get('graph')))
    output = output + dashes + '\n'

    return output
