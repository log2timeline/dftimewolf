# -*- coding: utf-8 -*-
"""Creates a GCP cloud resource tree."""

import json
import tempfile
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Dict, List, Optional, Any, Type

from dateutil import parser
from google.cloud import asset_v1
from libcloudforensics import errors
from libcloudforensics.providers.gcp.internal.common import CreateService
from libcloudforensics.providers.gcp.internal.compute import GoogleCloudCompute
from libcloudforensics.providers.gcp.internal.log import GoogleCloudLog

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class Resource:
  """A Class that represent a resource (Instance, Disk, Image...etc)."""

  has_dynamic_attributes = True  # silences all attribute-errors for Resource

  def __init__(self) -> None:
    """Initialize the Resource object."""
    self.id = ''
    self.name = ''

    self.type = ''
    self.state = ''
    self.project_id = ''
    self.zone = ''

    self.created_by = ''
    self.deleted_by = ''
    self.parent: Optional[Resource] = None
    self.children: List[Resource] = []
    self.disks: List[Resource] = []
    self.deleted = False
    self._resource_name = ''
    self._creation_timestamp: Optional[datetime] = None
    self._deletion_timestamp: Optional[datetime] = None

  def set_resource_name(self, value: str) -> None:
    """Property resource_name Sette."""
    if value:
      value = '/projects/' + value.split('/projects/')[-1]

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

      self.project_id = values[2]

      if value.find('zone'):
        self.zone = values[-3]
      elif value.find('global'):
        self.zone = 'global'

    self._resource_name = value

  def get_resource_name(self) -> str:
    """Property resource_name Getter."""
    return self._resource_name

  def set_creation_timestamp(self, value: datetime) -> None:
    """Property creation_timestamp Setter."""
    if isinstance(value, datetime):
      self._creation_timestamp = value
    else:
      self._creation_timestamp = parser.parse(value)

  def get_creation_timestamp(self) -> Optional[datetime]:
    """Property creation_timestamp Getter."""
    return self._creation_timestamp

  def set_deletion_timestamp(self, value: datetime) -> None:
    """Property deletion_timestamp Setter."""
    if isinstance(value, datetime):
      self._deletion_timestamp = value
    else:
      self._deletion_timestamp = parser.parse(value)

  def get_deletion_timestamp(self) -> Optional[datetime]:
    """Property deletion_timestamp Getter."""
    return self._deletion_timestamp

  resource_name = property(get_resource_name, set_resource_name)
  creation_timestamp = property(get_creation_timestamp, set_creation_timestamp)
  deletion_timestamp = property(get_deletion_timestamp, set_deletion_timestamp)

  def IsDeleted(self) -> bool:
    """Check if resource is deleted."""
    if self.deleted or self.deletion_timestamp or not self.creation_timestamp:
      return True

    return False

  def GenerateTree(self) -> List[Dict[str, 'Resource']]:
    """Generate the resource tree.

    Returns:
      List of dictionaries containing a reference to the resource and it name
      indented based on it's location in the tree
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
    output.extend(self._GenerateChildrenTree(level + 1))

    return output

  def _GenerateChildrenTree(self, level: int) -> List[Dict[str, 'Resource']]:
    """Generate the resource children tree.

    Args:
      level: The level in the tree to place the children at
    Returns:
      List of dictionaries containing a reference to the children resource and
      their names indented based on their location in the tree
    """
    result: List[Dict[str, Resource]] = []
    tab = '\t'

    for child in self.children:
      entry: Dict[str, Any] = {}
      entry['resource_object'] = child
      entry['graph'] = f'{tab*level}|--{child.name}'
      result.append(entry)

      if child.children:
        result.extend(child._GenerateChildrenTree(level + 1))

    return result

  def __str__(self) -> str:
    """Return a string representation of the resource tree."""
    output = '\n'
    dashes = '-' * 150

    # Draw table header
    output = output + dashes + '\n'
    output = output + '{:<25s}{:<25s}{:<25s}{:<25s}{:<25s}{:<100s}\n'.format(
        'ID', 'Type', 'Creation TimeStamp', 'Deletion Timestamp', 'Creator',
        'Tree')
    output = output + dashes + '\n'

    result = self.GenerateTree()
    for i in result:
      resource: Optional[Resource] = i.get('resource_object')
      if resource:
        output = output + \
            ('{:<25s}{:<25s}{:<25s}{:<25s}{:<25s}{:<100s} \n'.format(resource.id, resource.type, resource.creation_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if resource.creation_timestamp else "",
            resource.deletion_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if resource.deletion_timestamp else "", resource.created_by, i.get('graph')))

    return output


class GCPCloudResourceTree(module.BaseModule):
  """GCP Cloud Resource Tree Creator.

  input: None, takes input from parameters only.
  output: Temp file with a dump of the resource tree
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str] = None,
               critical: bool = True) -> None:
    """Initialize the Cloud Resource Tree Processor.

    Args:
      state: recipe state.
      name: The module's runtime name.
      critical: True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GCPCloudResourceTree, self).__init__(state,
                                               name=name,
                                               critical=critical)

    self._project_id = ''
    self._resource_name = ''
    self._resource_type = ''
    self._mode = ''
    self._start_date = ''
    self._end_date = ''
    # TODO Initialize this
    self._period_covered_by_retrieved_logs: Dict[str, Any] = {}
    self._resources_dict: Dict[str, Resource] = {}

  # pylint: disable=arguments-differ
  def SetUp(self, project_id: str, resource_name: str, resource_type: str,
            mode: str) -> None:
    """Set up the resource we want to build the tree for.

    Args:
      project_id: Project id where the resources are located.
      resource_name: Resource name.
      resource_type: Resource type (currently supported types: gce_instance,
        gce_disk, gce_image, gce_machine_image, gce_instance_template, gce_snapshot)
      mode: operational mode: online or offline
    """
    self._project_id = project_id
    self._resource_name = resource_name
    self._resource_type = resource_type
    self._mode = mode

  def Process(self) -> None:
    """Create the GCP Cloud Resource Tree."""
    if self._mode == 'offline':
      self.logger.info('Starting module in offline mode.')
      # Get the file containers created by the previous module in the recipe
      file_containers = self.state.GetContainers(containers.File)

      # Loop over the file containers and parse the content of each to fill the
      # resources dictionary
      for file_container in file_containers:
        self.logger.info(
            f'Loading file from file system container: {file_container.path}')
        self._ParseLogMessagesFromFileContainer(file_container)

      # Fix mapping caused by the lack of log entry for disks created
      # automatically with instances
      self._FixDisksMapping()

    else:
      self.logger.info('Starting module in online mode.')
      self._GetListOfResources(self._project_id)

    self._BuildResourcesParentRelationships()
    #self._BuildResourcesChildrenRelationships()

    matched_resources = self._GetResourceInfoByName(self._resource_name,
                                                    self._resource_type)

    if not matched_resources:
      self.logger.error('Resource not found')
      return

    if len(matched_resources) > 1:
      # TODO Ask the user which one should we work with or find a way to choose
      # to chose automatically. If online check the logs
      self.logger.warning(
          f'There are multiple resources with the same name: {self._resource_name}'
      )
    else:
      resource = matched_resources[0]

    # Build resource children tree
    resource.children = self._GetResourceChildrenTree(resource)

    # Save resource tree to temp file
    output_file = tempfile.NamedTemporaryFile(mode='w',
                                              delete=False,
                                              encoding='utf-8',
                                              suffix='.txt')
    output_path = output_file.name
    self.logger.info(f'Saving resource tree to {output_path}')
    with open(output_path, 'w') as out_file:
      out_file.write(str(resource))

    # Dump the resource tree to CLI
    self.logger.info(str(resource))

  def _GetListOfResources(self, project_id: str) -> None:
    """Acquire a list of resources under a project.

    Args:
      project_id: Project id to get list of resources from.
    """
    # Retrieve list of disks in a project
    self._resources_dict.update(self._RetrieveListOfDisks(project_id))

    # Retrieve list of snapshots in a project
    self._resources_dict.update(self._RetrieveListOfSnapshots(project_id))

    # Retrieve list of disk images in a project
    self._resources_dict.update(self._RetrieveListOfDiskImages(project_id))

    # Retrieve list of instances in a project
    self._resources_dict.update(self._RetrieveListOfInstances(project_id))

    # Retrieve list of machine images in a project
    self._resources_dict.update(self._RetrieveListOfMachineImages(project_id))

    # Retrieve list of instance templates in a project
    self._resources_dict.update(
        self._RetrieveListOfInstanceTemplate(project_id))

  def _GetResourceParentTree(self, resource: Resource) -> Optional[Resource]:
    """Return parent of a given resource.

    Args:
      resource: The resource object to get parents of

    Returns:
      resource object
    """
    if not resource:
      return None

    parent_resource: Optional[Resource] = None

    # The resource should at least have the name and type of the parent resource. This is
    # filled during the parsing of log messages in _ParesLogMessages() and/or _GetListOfResources
    if resource and resource.parent and resource.parent.name and resource.parent.type:
      if resource.parent.id:
        parent_resource = self._resources_dict.get(resource.parent.id)
        if not parent_resource:
          parent_resource = resource.parent
      else:
        matched_parent_resources = self._GetResourceInfoByName(
            resource.parent.name, resource.parent.type)
        if matched_parent_resources:
          parent_resource = matched_parent_resources[0]
        else:
          parent_resource = resource.parent

    elif resource and resource.disks:
      for disk in resource.disks:
        if disk and disk.name and disk.type:
          if disk.id:
            parent_resource = self._resources_dict.get(disk.id)
          else:
            matched_disks = self._GetResourceInfoByName(disk.name, disk.type)
            if not matched_disks:
              parent_resource = disk
            for matched_disk in matched_disks:
              if matched_disk.project_id == disk.project_id and matched_disk.zone == disk.zone:
                parent_resource = matched_disk
                break

    if parent_resource:
      if parent_resource.IsDeleted() and self._mode == 'online':
        found_resource = self._SearchForDeletedResource(
            parent_resource, resource.creation_timestamp, 'backward')
        if found_resource:
          if found_resource.id:
            self._resources_dict[found_resource.id] = found_resource
          parent_resource = found_resource

      # Recursively obtain parents for each resource in the chain
      parent_resource.parent = self._GetResourceParentTree(parent_resource)

    # Return the resource with all the parent chain filled
    return parent_resource

  def _FixDisksMapping(self) -> None:
    for resource in self._resources_dict.values():

      if not resource.disks:
        continue

      for disk in resource.disks:
        if not disk.id:
          matched_resources = self._GetResourceInfoByName(
              disk.name, disk.type, disk.project_id, disk.zone)
          if matched_resources:
            disk.id = matched_resources[0].id

          # Automatically created disks will have the same name as the instance
          if disk.name == resource.name:
            resource.parent = disk
            disk.children.append(resource)

  def _GetResourceChildrenTree(self, resource: Resource) -> List[Resource]:
    """Return the children of a given resource.

    Args:
      resource: The resource object to get children of

    Returns:
      List of resource objects
    """
    if not resource:
      return []

    children_resources: List[Resource] = []

    # Check if the child_resource has the same parent name as the resource we want
    # to obtain the children for. If true then add the child_resource to the
    # children_resources and recursively obtain children for the child_resource
    # itself.
    for child_resource in self._resources_dict.values():

      # skip if of the current resource returned by the loop is the
      # same as the resource we want to find the children for
      if child_resource.id == resource.id:
        continue

      # Check if the parent name of the current resource returned by the loop
      # is the same as the name of the resource we want to find the children for
      if child_resource and child_resource.parent:
        if child_resource.parent.id == resource.id:
          child_resource.children = self._GetResourceChildrenTree(
              child_resource)
          children_resources.append(child_resource)

        elif child_resource.parent.name == resource.name and child_resource.parent.zone == resource.zone:
          child_resource.children = self._GetResourceChildrenTree(
              child_resource)
          children_resources.append(child_resource)

      # If the current resource returned by the loop has disks (gce_instance,
      # gce_instance_template, gce_machine_image) and doesn't have a parent set
      # and the disk id is not set, and the parent resource name of the disk is
      # the name of the resource then we add the disk as a child to this
      # resource. This is due the disk create with no log entry issue
      if child_resource and child_resource.disks:
        for disk in child_resource.disks:
          if not disk.id and disk.parent and disk.parent.name == resource.name:
            children_resources.append(disk)

    return children_resources

  def _GetResourceInfoByName(self,
                             resource_name: str,
                             resource_type: str,
                             project_id: Optional[str] = None,
                             zone: Optional[str] = None) -> List[Resource]:
    """Search for a resource by name and type in the _resource_dict dictionary.

    Args:
      resource_name: Resource name.
      resource_type: Resource type (currently supported types: gce_instance,
        gce_disk, gce_image, gce_machine_image, gce_instance_template, gce_snapshot)

    Return:
      List of Resource object that match the name and type or None if a matching
      resource is not found

    """
    resources: List[Resource] = []

    # Search for the resource with the same name and type in the parsed logs.
    for resource in self._resources_dict.values():
      if resource.name == resource_name and resource.type == resource_type:
        resources.append(resource)

    # Filter list by project_id if it is supplied
    if project_id is not None:
      resources = [x for x in resources if x.project_id == project_id]

    # Filter list by zone if it is supplied
    if zone is not None:
      resources = [x for x in resources if x.zone in (zone, 'global')]

    return resources

  def _GetLogMessages(
      self,
      project_id: str,
      start_timestamp: str,
      end_timestamp: str,
      resource_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Acquire log messages from GCP logs for a specific project id and between a start and end timestamps.

    Args:
      project_id: Project id from which we are going to obtain the logs.
      start_timestamp: Retrieve logs starting at this timestamp.
      end_timestamp: Retrieve logs ending at this timestamp.

    Return:
      List of log messages
    """
    gcl = GoogleCloudLog(project_ids=[project_id])

    query_filter = f'resource.type = ("gce_instance" OR "api" OR "gce_disk" OR "gce_image" OR "gce_instance_template" OR "gce_snapshot") \
    AND logName = "projects/{project_id}/logs/cloudaudit.googleapis.com%2Factivity" \
    AND operation.first = "true" \
    AND timestamp >= "{start_timestamp}" \
    AND timestamp <= "{end_timestamp}" \
    AND severity=NOTICE \
    AND protoPayload.methodName : ("insert" OR "create" OR "delete")'

    if resource_id:
      query_filter = query_filter + \
          f' AND (resource.labels.instance_id="{resource_id}" OR resource.labels.image_id="{resource_id}")'

    log_messages: List[Dict[str,
                            Any]] = gcl.ExecuteQuery(qfilter=[query_filter])

    return log_messages

  def _ParseLogMessagesFromFileContainer(
      self, file_container: containers.File) -> None:
    """Parse GCP Cloud log messages supplied in the file container and fill the self._resource_dict with the result.

    Args:
      file_container: file container
    """
    if not file_container:
      self.logger.error('File container is null')
      return

    if not file_container.path:
      self.logger.error('File container path is null or empty')

    with open(file_container.path, 'r') as input_file:
      log_messages = []
      file_content = input_file.readline()

      if not file_content:
        self.logger.error(f'The supplied file {file_container.path} is empty')
        return

      while file_content:
        log_messages.append(json.loads(file_content))
        file_content = input_file.readline()

      self._ParseLogMessages(log_messages)

  def _ParseLogMessages(self, log_messages: List[Dict[str, Any]]) -> None:
    """Parse GCP Cloud log messages and fill the self._resource_dict with the result.

    Args:
      log_messages: list of log messages
    """
    for log_message in log_messages:

      proto_payload: Dict[str, Any] = log_message.get('protoPayload', {})

      if not proto_payload:
        continue

      request = proto_payload.get('request')
      response = proto_payload.get('response')
      if not request or not response:
        continue

      log_message_type = request.get('@type').split('/')[
          -1]  # Example: @type: "type.googleapis.com/compute.instances.insert"

      # Parse logs for supported resource types
      if log_message_type.startswith(
          ('compute.instances', 'compute.disks', 'compute.machineImages',
           'compute.image', 'compute.instanceTemplates', 'compute.snapshots')):
        # Only parse 'operation' responses, skipping errors
        if response.get('@type').split('/')[-1] != 'operation':
          continue

        resource = self._resources_dict.get(response.get('targetId'))

        # Check if a resource with the same ID already exist in the
        # self._resources_dict dictionary
        if not resource:
          resource = Resource()

        resource.id = response.get('targetId')
        resource.state = response.get('status')

        # compute.disks.createSnapshot is a special case where the
        # "resourceName" is just the name and not the full name with the
        # project, zone, type and name
        if log_message_type.startswith('compute.disks.createSnapshot'):
          # TODO Build the resource_name in the Resource class.
          resource.name = request.get('name')
          # GCP Log issue, the resource.type is set to 'gce_disk' so i am
          # setting it manually to gce_snapshot
          resource.type = 'gce_snapshot'
          resource.project_id = log_message.get('resource',
                                                {}).get('labels',
                                                        {}).get('project_id')
          resource.zone = log_message.get('resource', {}).get('labels',
                                                              {}).get('zone')

        else:
          resource.resource_name = proto_payload.get('resourceName')

        # In case the message is an insert message
        if log_message_type.endswith('insert') or log_message_type.endswith(
            'createSnapshot'):
          resource = self._ParseInsertLogMessage(resource, request, response)

        elif log_message_type.endswith('delete'):
          resource.deletion_timestamp = response.get('insertTime')
          resource.deleted_by = response.get('user')

      else:
        self.logger.info(f'Type {log_message_type} not supported')
        resource = None

      if resource and resource.id:
        self._resources_dict[resource.id] = resource

  def _ParseInsertLogMessage(self, resource: Resource, request: Dict[str, Any],
                             response: Dict[str, Any]) -> Resource:
    """Parse a GCP log message where the operation is insert or create.

    Args:
      resource: Resource object to update with parsed information
      request: Request portion of the log message
      response: Response portion of the log message

    Returns:
      Resource object filled with data parsed from the Log message
    """
    resource.creation_timestamp = response.get('insertTime')
    resource.created_by = response.get('user', '')

    if 'sourceDisk' in request:
      if not resource.parent:
        resource.parent = Resource()
      resource.parent.resource_name = request.get('sourceDisk')

    if 'sourceMachineImage' in request:  # When creating an instance from a machine image
      if not resource.parent:
        resource.parent = Resource()
      resource.parent.resource_name = request.get('sourceMachineImage')

    elif 'sourceInstance' in request:  # Source of image
      if not resource.parent:
        resource.parent = Resource()
      resource.parent.resource_name = request.get('sourceInstance')

    elif 'sourceSnapshot' in request:
      if not resource.parent:
        resource.parent = Resource()
      resource.parent.resource_name = request.get('sourceSnapshot')

    else:
      # When creating a new instance, one of
      # initializeParams.sourceImage or initializeParams.sourceSnapshot or
      # disks.source is required except for local SSD.
      if request.get('disks'):
        for disk in request.get('disks', {}):
          disk_resource = Resource()
          disk_resource.name = disk.get('deviceName')
          disk_resource.type = 'gce_disk'
          disk_resource.zone = resource.zone
          disk_resource.project_id = resource.project_id

          # Check if we already have the disk in the _resources_dict. If true
          # then add it to the resource disks list and continue to next disk.
          matched_resources = self._GetResourceInfoByName(
              disk_resource.name, disk_resource.type, disk_resource.project_id,
              disk_resource.zone)
          if matched_resources:
            resource.disks.append(matched_resources[0])
            continue

          initialize_params = disk.get('initializeParams')
          if initialize_params:

            if 'sourceImage' in initialize_params:
              if not disk_resource.parent:
                disk_resource.parent = Resource()
              disk_resource.parent.resource_name = initialize_params.get(
                  'sourceImage')

            elif 'sourceSnapshot' in initialize_params:
              if not disk_resource.parent:
                disk_resource.parent = Resource()
              disk_resource.parent.resource_name = initialize_params.get(
                  'sourceSnapshot')

          elif 'source' in disk:  # cloned disk falls here
            if not disk_resource.parent:
              disk_resource.parent = Resource()
            disk_resource.parent.resource_name = disk.get('source')

          # This is an exceptional case cause the logs don't have an entry
          # for disks being created automatically when a gce_instance is
          # created. The automatically created disk has the same name as the gce_instance
          if disk_resource.name == resource.name:
            disk_resource.creation_timestamp = resource.creation_timestamp

          resource.disks.append(disk_resource)

          if disk_resource.parent:
            matched_resources = self._GetResourceInfoByName(
                disk_resource.parent.name, disk_resource.parent.type,
                disk_resource.parent.project_id, disk_resource.parent.zone)
            if matched_resources:
              disk_resource.parent = matched_resources[0]

    if resource.parent:
      matched_resources = self._GetResourceInfoByName(
          resource.parent.name, resource.parent.type,
          resource.parent.project_id, resource.parent.zone)
      if matched_resources:
        resource.parent = matched_resources[0]

    return resource

  def _BuildResourcesParentRelationships(self) -> None:
    """Build parent relationship for all resources."""
    # Using resource_keys because self._resources_dict changes during the loop
    resource_keys = list(self._resources_dict.keys())
    for resource_key in resource_keys:
      resource = self._resources_dict.get(resource_key)
      if resource:
        resource.parent = self._GetResourceParentTree(resource)

  def _BuildResourcesChildrenRelationships(self) -> None:
    """Build children relationship for all resources."""
    for resource in self._resources_dict.values():
      resource.children = self._GetResourceChildrenTree(resource)

  def _SearchForDeletedResource(self, resource: Resource,
                                start_timestamp: datetime,
                                direction: str) -> Optional[Resource]:
    """Search for deleted resource in GCP Logs.

    Args:
      resource: resource to search for.
      start_timestamp: the initial point of time to start the search
      direction: whether to go backwards or forwards in time

    Return:
      Found resource or None
    """
    if not resource or not start_timestamp or not direction:
      return None

    if resource.project_id != self._project_id:
      return None

    if not self._period_covered_by_retrieved_logs.get('start'):
      self._period_covered_by_retrieved_logs['start'] = start_timestamp
    if not self._period_covered_by_retrieved_logs.get('end'):
      self._period_covered_by_retrieved_logs['end'] = start_timestamp

    if direction == 'backward':

      while start_timestamp > (datetime.now(timezone.utc) -
                               timedelta(days=400)):

        end_timestamp = start_timestamp + timedelta(minutes=20)
        start_timestamp = start_timestamp - timedelta(days=30)

        if start_timestamp < self._period_covered_by_retrieved_logs.get(
            'start', {}):
          self._period_covered_by_retrieved_logs['start'] = start_timestamp
          if end_timestamp < self._period_covered_by_retrieved_logs.get(
              'end', {}):
            end_timestamp = self._period_covered_by_retrieved_logs.get(
                'start', {})

        if end_timestamp > self._period_covered_by_retrieved_logs.get(
            'end', {}):
          self._period_covered_by_retrieved_logs['end'] = end_timestamp
          if start_timestamp > self._period_covered_by_retrieved_logs.get(
              'start', {}):
            start_timestamp = self._period_covered_by_retrieved_logs.get(
                'end', {})

        else:
          continue

        print(
            f'Searching between {start_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} and {end_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} for {resource.name} {resource.type}'
        )
        log_messages = self._GetLogMessages(
            resource.project_id,
            start_timestamp.astimezone(
                timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            end_timestamp.astimezone(
                timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), resource.id)
        self._ParseLogMessages(log_messages)

        matched_resource = self._GetResourceInfoByName(resource.name,
                                                       resource.type)
        if matched_resource:
          if matched_resource[0].deletion_timestamp and matched_resource[
              0].creation_timestamp:
            return matched_resource[0]

    return None

  def _RetrieveListOfDisks(self, project_id: str) -> Dict[str, Resource]:
    """Retrieve list of disks in a project.

    Args:
      project_id: Project Id to retrieve the list of disks for

    Returns:
      Dict of disks
    """
    result: Dict[str, Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = CreateService('compute', 'beta')

    request = compute_api_client.disks().aggregatedList(project=project_id)

    while request is not None:
      response = request.execute()

      for zone in response['items'].values():
        # If the zone doesn't have any disks, move to next one.
        if not zone.get('disks'):
          continue

        for disk in zone.get('disks'):
          resource = Resource()
          resource.id = disk.get('id')
          resource.resource_name = disk.get('selfLink')
          resource.creation_timestamp = disk.get('creationTimestamp')
          if disk.get('sourceDisk'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = disk.get('sourceDisk')
            resource.parent.id = disk.get('sourceDiskId')
          elif disk.get('sourceSnapshot'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = disk.get('sourceSnapshot')
            resource.parent.id = disk.get('sourceSnapshotId')
          elif disk.get('sourceImage'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = disk.get('sourceImage')
            resource.parent.id = disk.get('sourceImageId')

          result[resource.id] = resource

      request = compute_api_client.disks().aggregatedList_next(
          previous_request=request, previous_response=response)

    return result

  def _RetrieveListOfDiskImages(self, project_id: str) -> Dict[str, Resource]:
    """Retrieve list of disk images in a project.

    Args:
      project_id: Project Id to retrieve the list of disk images for

    Return:
      Dict of disk images
    """
    result: Dict[str, Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = CreateService('compute', 'beta')

    # Disk images are not tied to a zone, so there is no aggregatedList
    request = compute_api_client.images().list(project=project_id)

    while request is not None:
      response = request.execute()

      if response and response.get('items'):
        for image in response.get('items'):
          resource = Resource()
          resource.id = image.get('id')
          resource.resource_name = image.get('selfLink')
          resource.creation_timestamp = image.get('creationTimestamp')
          if image.get('sourceDisk'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = image.get('sourceDisk')
            resource.parent.id = image.get('sourceDiskId')
          elif image.get('sourceSnapshot'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = image.get('sourceSnapshot')
            resource.parent.id = image.get('sourceSnapshotId')
          result[resource.id] = resource

      request = compute_api_client.images().list_next(
          previous_request=request, previous_response=response)

    return result

  def _RetrieveListOfInstances(self, project_id: str) -> Dict[str, Resource]:
    """Retrieve list of instances in a project.

    Args:
      project_id: Project Id to retrieve the list of instances for

    Returns:
      Dict of instances
    """
    result: Dict[str, Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = CreateService('compute', 'beta')

    request = compute_api_client.instances().aggregatedList(project=project_id)

    while request is not None:
      response = request.execute()

      for zone in response['items'].values():
        # If the zone doesn't have any instances, move to next one.
        if not zone.get('instances'):
          continue

        for instance in zone.get('instances'):
          resource = Resource()
          resource.id = instance.get('id')
          resource.resource_name = instance.get('selfLink')
          resource.creation_timestamp = instance.get('creationTimestamp')

          if instance.get('sourceMachineImage'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = instance.get('sourceMachineImage')
          else:
            for disk in instance.get('disks'):
              temp_disk = Resource()
              if disk.get('source'):
                temp_disk.resource_name = disk.get('source')
                matched_disks = self._GetResourceInfoByName(
                    temp_disk.name, temp_disk.type)
                for matched_disk in matched_disks:
                  if matched_disk.resource_name == temp_disk.resource_name:
                    temp_disk = matched_disk

              resource.disks.append(temp_disk)

          result[resource.id] = resource

      request = compute_api_client.instances().aggregatedList_next(
          previous_request=request, previous_response=response)

    return result

  def _RetrieveListOfSnapshots(self, project_id: str) -> Dict[str, Resource]:
    """Retrieve list of snapshots in a project.

    Args:
      project_id: Project Id to retrieve the list of snapshots for

    Returns:
      Dict of snapshots
    """
    result: Dict[str, Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = CreateService('compute', 'beta')

    request = compute_api_client.snapshots().list(project=project_id)

    while request is not None:
      response = request.execute()

      if response and response.get('items'):
        for snapshot in response['items']:
          resource = Resource()
          resource.id = snapshot.get('id')
          resource.resource_name = snapshot.get('selfLink')
          resource.creation_timestamp = snapshot.get('creationTimestamp')
          if snapshot.get('sourceDisk'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = snapshot.get('sourceDisk')
            resource.parent.id = snapshot.get('sourceDiskId')
          result[resource.id] = resource

      request = compute_api_client.snapshots().list_next(
          previous_request=request, previous_response=response)

    return result

  def _RetrieveListOfInstanceTemplate(self,
                                      project_id: str) -> Dict[str, Resource]:
    """Retrieve list of instance templates in a project.

    Args:
      project_id: Project Id to retrieve the list of instance templates for

    Returns:
      Dict of instance templates
    """
    result: Dict[str, Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = CreateService('compute', 'beta')

    # Retrieve list of instance templates in a project
    request = compute_api_client.instanceTemplates().list(project=project_id)

    while request is not None:
      response = request.execute()

      if response and response.get('items'):
        for instance_template in response.get('items'):
          resource = Resource()
          resource.id = instance_template.get('id')
          resource.resource_name = instance_template.get('selfLink')
          resource.creation_timestamp = instance_template.get(
              'creationTimestamp')

          for disk in instance_template.get('properties', {}).get('disks', {}):
            disk_resource = Resource()
            if disk.get('source'):
              disk_resource.resource_name = disk.get('source')
            elif disk.get('deviceName'):
              disk_resource.name = disk.get('deviceName')
              if disk.get('initializeParams'):
                if disk.get('initializeParams').get('sourceImage'):
                  disk_resource.parent = Resource()
                  disk_resource.parent.resource_name = disk.get(
                      'initializeParams').get('sourceImage')
            resource.disks.append(disk_resource)
          result[resource.id] = resource

      request = compute_api_client.instanceTemplates().list_next(
          previous_request=request, previous_response=response)

    return result

  def _RetrieveListOfMachineImages(self,
                                   project_id: str) -> Dict[str, Resource]:
    """Retrieve list of machine images in a project.

    Args:
      project_id: Project Id to retrieve the list of machine images for

    Returns:
      Dict of machine images
    """
    result: Dict[str, Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = CreateService('compute', 'beta')

    request = compute_api_client.machineImages().list(project=project_id)

    while request is not None:
      response = request.execute()

      if response and response.get('items'):
        for machine_image in response.get('items'):
          # Parse disks
          resource = Resource()
          resource.id = machine_image.get('id')
          resource.resource_name = machine_image.get('selfLink')
          resource.creation_timestamp = machine_image.get('creationTimestamp')
          if machine_image.get('sourceInstance'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = machine_image.get('sourceInstance')
          result[resource.id] = resource

      request = compute_api_client.machineImages().list_next(
          previous_request=request, previous_response=response)

    return result


modules_manager.ModulesManager.RegisterModule(GCPCloudResourceTree)
