# -*- coding: utf-8 -*-
"""Helper classes for the GCP cloud resource tree module."""
import datetime
import enum
import io
import json
from typing import Dict, List, Optional, Any, Set, Union
import pandas as pd


class OperatingMode(enum.Enum):
  """Enum represent operational mode (Online or Offline)."""

  ONLINE = enum.auto()
  OFFLINE = enum.auto()


class LocationType(enum.Enum):
  """Enum represent location type (Zone or Region or Global)."""

  ZONE = enum.auto()
  REGION = enum.auto()
  GLOBAL = enum.auto()


class Resource():
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
      in
      http://cloud/compute/docs/logging/migrating-from-activity-logs-to-audit-logs#fields.
    _creation_timestamp (Optional[datetime]): Resource creation timestamp.
    _deletion_timestamp (Optional[datetime]): Resource deletion timestamp.
  """

  has_dynamic_attributes = True  # silences all attribute-errors for Resource
  _TAB = '|----'

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
    self._creation_timestamp: Optional[datetime.datetime] = None
    self._deletion_timestamp: Optional[datetime.datetime] = None

  def __hash__(self) -> int:
    """For object comparison."""
    return hash(self.id + self.resource_name)

  @property
  def resource_name(self) -> str:
    """Property resource_name Getter."""
    if (not self._resource_name and self.name and self.project_id
        and self.location):
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
        return f"""projects/{
          self.project_id}/regions/{self.location}/{tmp_type}/{self.name}"""
      if self.location_type == LocationType.ZONE:
        return f"""projects/{
          self.project_id}/zones/{self.location}/{tmp_type}/{self.name}"""

    return self._resource_name

  @resource_name.setter
  def resource_name(self, value: str) -> None:
    """Property resource_name Setter.

       This property setter function will split the resource_name and set the
       "type", "location", "project_id" and "name" of the resource.

    Args:
      value: value to set resource_name to.
    """
    # value example:
    # 1- If parsing logs: projects/test-project/zones/us-central1-a/disks/vm1
    # 2- If querying resource through API call:
    #     //www.googleapis.com/compute/beta/projects/test-project/zones/us-central1-a/disks/vm1 # pylint: disable=line-too-long
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
  def creation_timestamp(self) -> Optional[datetime.datetime]:
    """Property creation_timestamp Getter."""
    return self._creation_timestamp

  @creation_timestamp.setter
  def creation_timestamp(self, value: Union[datetime.datetime, str]) -> None:
    """Property creation_timestamp Setter.

    Args:
      value: value to set the creation_timestamp to.
    """
    if isinstance(value, datetime.datetime):
      self._creation_timestamp = value
    else:
      self._creation_timestamp = datetime.datetime.strptime(
          value, '%Y-%m-%dT%H:%M:%S.%f%z')

  @property
  def deletion_timestamp(self) -> Optional[datetime.datetime]:
    """Property deletion_timestamp Getter."""
    return self._deletion_timestamp

  @deletion_timestamp.setter
  def deletion_timestamp(self, value: Union[datetime.datetime, str]) -> None:
    """Property deletion_timestamp Setter.

    Args:
      value: value to set the deletion_timestamp to.
    """
    if isinstance(value, datetime.datetime):
      self._deletion_timestamp = value
    else:
      self._deletion_timestamp = datetime.datetime.strptime(
          value, '%Y-%m-%dT%H:%M:%S.%f%z')

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
        entry['tree'] = f'{self._TAB*counter}{parent_resource.name}'
        output.insert(0, entry)
        if parent_resource.parent:
          parent_resource = parent_resource.parent

    # Add resource entry to the List of dictionaries
    entry = {}
    entry['resource_object'] = self
    entry['tree'] = f'{self._TAB*level}{self.name}'
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

    for child in self.children:
      entry: Dict[str, Any] = {}
      entry['resource_object'] = child
      entry['tree'] = f'{self._TAB*level}{child.name}'
      result.append(entry)

      if child.children:
        result.extend(child.GenerateChildrenTree(level + 1))

    return result

  def __str__(self) -> str:
    """Returns a string representation of the resource tree."""
    output = io.StringIO('')
    # output = '\n'
    dashes = '-' * 200
    # Draw table header
    output.write(f'\n{dashes}\n')
    output.write(f'{"Resource ID":<20s}|{"Resource Type":<18s}|' +
                 f'{"Creation TimeStamp":<20s}|{"Created By":<25s}|' +
                 f'{"Creator IP Addr":<18s}|{"Deletion Timestamp":<20s}|' +
                 f'{"Deleted By":<25s}|{"Deleter IP Addr":<18s}|' +
                 f'{"Tree":<100s}\n')
    output.write(f'{dashes}\n')

    # Generate resource tree
    result = self.GenerateTree()

    # Draw table rows
    for entry in result:
      resource: Optional[Resource] = entry.get('resource_object')
      if resource:
        output.write(
          # pylint: disable=line-too-long
          # If the resource.id contains a '-' then its a fake one we created for tracking so we are not displaying it in the output
          f'{resource.id if (resource.id and "-" not in resource.id) else "":<20s}|'
          + f'{resource.type if resource.type else "":<18s}|'
          + f"""{resource.creation_timestamp.astimezone(
                        datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                        if resource.creation_timestamp else "":<20s}|"""
          + f'{resource.created_by if resource.created_by else "":<25s}|'
          + f'{resource.creator_ip_address if resource.creator_ip_address else "":<18s}|'
          + f"""{resource.deletion_timestamp.astimezone(
                        datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                        if resource.deletion_timestamp else "":<20s}|"""
          + f'{resource.deleted_by if resource.deleted_by else "":<25s}|'
          + f'{resource.deleter_ip_address if resource.deleter_ip_address else "":<18s}|'
          + f'{entry.get("tree"):<100s}\n'
          # pylint: enable=line-too-long
        )
    output.write(f'{dashes} \n')

    return output.getvalue()

  def AsDict(self) -> Dict[str, Any]:
    """Returns a dictionary representation of the resource object."""
    creation_timestamp = ""
    if self.creation_timestamp:
      assert self.creation_timestamp is not None
      creation_timestamp = self.creation_timestamp.astimezone(
        datetime.timezone.utc
      ).strftime("%Y-%m-%dT%H:%M:%SZ")
    deletion_timestamp = ""
    if self.deletion_timestamp:
      assert self.deletion_timestamp is not None
      deletion_timestamp = self.deletion_timestamp.astimezone(
        datetime.timezone.utc
      ).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
      "id": self.id,
      "name": self.name,
      "type": self.type,
      "project_id": self.project_id,
      "location": self.location,
      "created_by": self.created_by,
      "creator_ip_address": self.creator_ip_address,
      "creator_useragent": self.creator_useragent,
      "deleted_by": self.deleted_by,
      "deleter_ip_address": self.deleter_ip_address,
      "deleter_useragent": self.deleter_useragent,
      "resource_name": self.resource_name,
      "creation_timestamp": creation_timestamp,
      "deletion_timestamp": deletion_timestamp,
    }

  def ToDataFrame(self) -> pd.DataFrame:
    """Returns a DataFrame representation of the resource tree."""
    result = self.GenerateTree()
    output = []
    for entry in result:
      if not entry.get('resource_object'):
        continue
      resource_dict = entry['resource_object'].AsDict()
      resource_dict['tree'] = entry.get('tree')
      output.append(resource_dict)
    df = pd.DataFrame.from_records(output)
    df.loc[df['id'].str.contains('-'), 'id'] = ''
    # Rearrange columns
    df = df[[
        'id', 'name', 'type', 'project_id', 'location', 'tree',
        'creation_timestamp', 'created_by', 'creator_ip_address',
        'creator_useragent', 'deletion_timestamp', 'deleted_by',
        'deleter_ip_address', 'deleter_useragent', 'resource_name'
    ]]
    return df


class ResourceEncoder(json.JSONEncoder):
  """A Class that implements custom json encoding for Resource object."""

  def default(self, o: Resource) -> Dict[str, Optional[Resource]]:
    """Returns a dictionary representation of the resource object."""
    if isinstance(o, Resource):
      return o.AsDict()

    return super().default(o)
