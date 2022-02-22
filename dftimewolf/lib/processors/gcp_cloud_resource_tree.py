# -*- coding: utf-8 -*-
"""Creates a GCP cloud resource tree."""

import json
import tempfile
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Optional
from typing import Dict

from dateutil import parser
from google.cloud import asset_v1
from google.protobuf.timestamp_pb2 import Timestamp
from libcloudforensics import errors
from libcloudforensics.providers.gcp.internal.common import CreateService
from libcloudforensics.providers.gcp.internal.compute import GoogleCloudCompute
from libcloudforensics.providers.gcp.internal.log import GoogleCloudLog

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class Resource:
  """An Class that represent a resource (Instance, Disk, Image...etc)."""
  has_dynamic_attributes = True  # silences all attribute-errors for Resource

  def __init__(self):
    self.id = ''
    self.name = None

    self.type = ''
    self.state = None
    self.project_id = None
    self.zone = None

    self.created_by = ''
    self.deleted_by = ''
    self.parent = None
    self.children = []
    self.disks = []
    self.deleted = False
    self._resource_name = None
    self._creation_timestamp = None
    self._deletion_timestamp = None

  def set_resource_name(self, value):
    """Property resource_name Setter"""

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

  def get_resource_name(self):
    """Property resource_name Getter"""
    return self._resource_name

  def set_creation_timestamp(self, value):
    """Property creation_timestamp Setter"""
    if isinstance(value, datetime):
      self._creation_timestamp = value
    else:
      self._creation_timestamp = parser.parse(value)

  def get_creation_timestamp(self):
    """Property creation_timestamp Getter"""
    return self._creation_timestamp

  def set_deletion_timestamp(self, value):
    """Property deletion_timestamp Setter"""
    if isinstance(value, datetime):
      self._deletion_timestamp = value
    else:
      self._deletion_timestamp = parser.parse(value)

  def get_deletion_timestamp(self):
    """Property deletion_timestamp Getter"""
    return self._deletion_timestamp

  resource_name = property(get_resource_name, set_resource_name)
  creation_timestamp = property(get_creation_timestamp, set_creation_timestamp)
  deletion_timestamp = property(get_deletion_timestamp, set_deletion_timestamp)

  def IsDeleted(self):
    """Check if resource is deleted"""
    if self.deleted or self.deletion_timestamp or not self.creation_timestamp:
      return True
    else:
      return False

  def GenerateTree(self) -> List[Dict]:
    """Generates the resource tree

    Returns:
      List of dictionaries containing a reference to the resource and it name
      indented based on it's location in the tree
    """
    tab = '\t'
    output = []

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
    while counter > 0:
      counter = counter - 1
      entry = {}
      entry['resource_object'] = parent_resource
      entry['graph'] = f'{tab*counter}|--{parent_resource.name}'
      output.insert(0, entry)
      parent_resource = parent_resource.parent

    # Add resource entry to the List of dictionaries
    entry = {}
    entry['resource_object'] = self
    entry['graph'] = f'{tab*level}|--{self.name}'
    output.insert(level, entry)

    # Add resource children entries to the List of dictionaries
    output.extend(self._GenerateChildrenTree(level + 1))

    return output

  def _GenerateChildrenTree(self, level) -> List[Dict]:
    """Generates the resource children tree.
    Args:
      level: The level in the tree to place the children at
    Returns:
      List of dictionaries containing a reference to the children resource and
      their names indented based on their location in the tree
    """
    result = []
    tab = '\t'

    for child in self.children:
      entry = {}
      entry['resource_object'] = child
      entry['graph'] = f'{tab*level}|--{child.name}'
      result.append(entry)

      if child.children:
        result.extend(child._GenerateChildrenTree(level + 1))

    return result

  def __str__(self):
    """Retrun a string representation of the resource tree."""
    output = '\n'
    dashs = '-' * 150

    # Draw table header
    output = output + dashs + '\n'
    output = output + '{:<25s}{:<25s}{:<25s}{:<25s}{:<15s}{:<100s}\n'.format(
        'ID', 'Type', 'Creation TimeStamp', 'Deletion Timestamp', 'Is Deleted',
        'Tree')
    output = output + dashs + '\n'

    result = self.GenerateTree()
    for i in result:
      resource = i.get('resource_object')
      output = output + \
          ('{:<25s}{:<25s}{:<25s}{:<25s}{:<15s}{:<100s} \n'.format(resource.id, resource.type, resource.creation_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if resource.creation_timestamp else "",
           resource.deletion_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if resource.deletion_timestamp else "", "Yes" if resource.IsDeleted() else "No", i.get('graph')))

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
    """Initializes the Cloud Resource Tree Processor.

    Args:
      state: recipe state.
      name: The module's runtime name.
      critical: True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """

    super(GCPCloudResourceTree, self).__init__(
        state, name=name, critical=critical)

    self._project_id = ''
    self._resource_name = ''
    self._resource_type = ''
    self._mode = ''
    self._start_date = ''
    self._end_date = ''
    # TODO Initialize this
    self._period_covered_by_retrieved_logs = {}
    self._resources_dict = {}

  # pylint: disable=arguments-differ
  def SetUp(self, project_id: str, resource_name: str, resource_type: str,
            mode: str, start_date: Optional[str] = None,
            end_date: Optional[str] = None) -> None:
    """Sets up the resource we want to build the tree for.

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

    else:
      self.logger.info('Starting module in online mode.')
      self._GetResourceInfoFromBatchHistory(
          self._project_id, "us-central1-a", "dm-2", "images")
      return
      # self._GetListOfResources(self._project_id)

    self._BuildResourcesParentRelateionship()

    matched_resources = self._GetResourceInfoByName(
        self._resource_name, self._resource_type)

    if not matched_resources:
      self.logger.error('Resource not found')
      return
    elif len(matched_resources) > 1:
      # TODO Ask the user which one should we work with or find a way to choose
      # to chose automatically. If online check the logs
      self.logger.warning('There are multiple resources with the same name')
    else:
      resource = matched_resources[0]

    # Get resource parents
    # resource.parent = self._GetResourceParent(resource)

    # Get resource children
    resource.children = self._GetResourceChildren(resource)

    # Save resource tree to temp file
    output_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, encoding='utf-8', suffix='.txt')
    output_path = output_file.name
    self.logger.info(f'Saving resource tree to {output_path}')
    with open(output_path, 'w') as out_file:
      out_file.write(str(resource))

    # Dump the resource tree to CLI
    self.logger.info(str(resource))

  def _GetListOfResources(self, project_id: str):
    """Acquire a list of resources under a project.

    Args:
      project_id: Project id to get list of resources from.
    """

    disks_dict = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = CreateService(
        'compute', 'beta')

    # Retrive list of disks in a project
    request = compute_api_client.disks().aggregatedList(
        project=self._project_id)

    while request is not None:
      response = request.execute()

      for disks_scoped_list in response['items'].values():
        # If the zone doesn't have any disks, move to next one.
        if not disks_scoped_list.get('disks'):
          continue

        for disk in disks_scoped_list.get('disks'):
          resource = Resource()
          resource.id = disk.get('id')
          resource.resource_name = '/projects/' + \
              disk.get('selfLink').split('/projects/')[-1]
          resource.creation_timestamp = disk.get('creationTimestamp')
          if disk.get('sourceDisk'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = disk.get('sourceDisk')
            if disk.get('sourceDiskId'):
              resource.parent.id = disk.get('sourceDiskId')
          elif disk.get('sourceSnapshot'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = disk.get('sourceSnapshot')
            if disk.get('sourceSnapshotId'):
              resource.parent.id = disk.get('sourceSnapshotId')
          elif disk.get('sourceImage'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = disk.get('sourceImage')
            if disk.get('sourceImageId'):
              resource.parent.id = disk.get('sourceImageId')

          #disks_dict[resource.resource_name] = resource
          self._resources_dict[resource.id] = resource

      request = compute_api_client.disks().aggregatedList_next(
          previous_request=request, previous_response=response)

    # Retrive list of snapshots in a project
    request = compute_api_client.snapshots().list(project=self._project_id)

    while request is not None:
      response = request.execute()

      if response and response.get('items'):
        for snapshot in response['items']:
          resource = Resource()
          resource.id = snapshot.get('id')
          resource.resource_name = '/projects/' + \
              snapshot.get('selfLink').split('/projects/')[-1]
          resource.creation_timestamp = snapshot.get('creationTimestamp')
          if snapshot.get('sourceDisk'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = snapshot.get('sourceDisk')
            if snapshot.get('sourceDiskId'):
              resource.parent.id = snapshot.get('sourceDiskId')
          self._resources_dict[resource.id] = resource

      request = compute_api_client.snapshots().list_next(
          previous_request=request, previous_response=response)

    # Retrive list of disk images in a project
    request = compute_api_client.images().list(project=self._project_id)

    while request is not None:
      response = request.execute()

      if response and response.get('items'):
        for image in response.get('items'):
          resource = Resource()
          resource.id = image.get('id')
          resource.resource_name = '/projects/' + \
              image.get('selfLink').split('/projects/')[-1]
          resource.creation_timestamp = image.get('creationTimestamp')
          if image.get('sourceDisk'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = image.get('sourceDisk')
            if image.get('sourceDiskId'):
              resource.parent.id = image.get('sourceDiskId')

          elif image.get('sourceSnapshot'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = image.get('sourceSnapshot')
            if image.get('sourceSnapshotId'):
              resource.parent.id = image.get('sourceSnapshotId')
          self._resources_dict[resource.id] = resource

      request = compute_api_client.images().list_next(
          previous_request=request, previous_response=response)

    # Retrive list of instances in a project
    request = compute_api_client.instances().aggregatedList(
        project=self._project_id)

    while request is not None:
      response = request.execute()

      for instances_scoped_list in response['items'].values():
        # If the zone doesn't have any instances, move to next one.
        if not instances_scoped_list.get('instances'):
          continue

        for instance in instances_scoped_list.get('instances'):
          resource = Resource()
          resource.id = instance.get('id')
          resource.resource_name = '/projects/' + \
              instance.get('selfLink').split('/projects/')[-1]
          resource.creation_timestamp = instance.get('creationTimestamp')

          if instance.get('sourceMachineImage'):
            print(instance)
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = instance.get(
                'sourceMachineImage')
          else:
            for disk in instance.get('disks'):
              # disk_resource_name = '/projects/' + \
              #     disk.get('source').split('/projects/')[-1]
              # disk_resource = disks_dict.get(disk_resource_name)
              # if disk_resource:
              #   resource.disks.append(
              #       self._resources_dict.get(disk_resource.id))
              #   resource.disks.append(
              #       self._resources_dict.get(disk_resource.id))
              #   print('Disk with no ID reached')

              disk_resource = Resource()
              if disk.get('source'):
                disk_resource.resource_name = '/projects/' + \
                    disk.get('source').split('/projects/')[-1]
              elif disk.get('deviceName'):
                disk_resource.name = disk.get('deviceName')
              #disk_resource.resource_name = disk.get('source')
              resource.disks.append(disk_resource)

          self._resources_dict[resource.id] = resource

      request = compute_api_client.instances().aggregatedList_next(
          previous_request=request, previous_response=response)

    # Retrive list of machine images in a project
    request = compute_api_client.machineImages().list(project=self._project_id)

    while request is not None:
      response = request.execute()

      if response and response.get('items'):
        for machine_image in response.get('items'):
          # Parse disks
          resource = Resource()
          resource.id = machine_image.get('id')
          resource.resource_name = '/projects/' + \
              machine_image.get('selfLink').split('/projects/')[-1]
          resource.creation_timestamp = machine_image.get(
              'creationTimestamp')
          if machine_image.get('sourceInstance'):
            if not resource.parent:
              resource.parent = Resource()
            resource.parent.resource_name = machine_image.get(
                'sourceInstance')
          self._resources_dict[resource.id] = resource

      request = compute_api_client.machineImages().list_next(
          previous_request=request, previous_response=response)

    # Retrive list of instance templates in a project
    request = compute_api_client.instanceTemplates().list(project=self._project_id)

    while request is not None:
      response = request.execute()

      if response and response.get('items'):
        for instance_template in response.get('items'):
          # TODO: Change code below to process each `instance` resource:
          resource = Resource()
          resource.id = instance_template.get('id')
          resource.resource_name = '/projects/' + \
              instance_template.get('selfLink').split('/projects/')[-1]
          resource.creation_timestamp = instance_template.get(
              'creationTimestamp')
          print(instance_template.get('properties', {}).get('disks', {}))

          for disk in instance_template.get('properties', {}).get('disks', {}):
            disk_resource = Resource()
            if disk.get('source'):
              disk_resource.resource_name = '/projects/' + \
                  disk.get('source').split('/projects/')[-1]
            elif disk.get('deviceName'):
              disk_resource.name = disk.get('deviceName')
              if disk.get('initializeParams'):
                if disk.get('initializeParams').get('sourceImage'):
                  disk_resource.parent = Resource()
                  disk_resource.parent.resource_name = disk.get(
                      'initializeParams').get('sourceImage')
            resource.disks.append(disk_resource)
          self._resources_dict[resource.id] = resource

      request = compute_api_client.instanceTemplates().list_next(
          previous_request=request, previous_response=response)

    return

  def _GetResourceParent(self, resource: Resource) -> Resource:
    """Return parent of a given resource.

    Args:
      resource: The resource object to get parents of

    Returns:
      resource object
    """

    if not resource:
      return None

    parent_resource = None

    # The resource should at least have the name and type of the parent resource. This is
    # filled during the parsing of log messages in _ParesLogMessages() and/or _GetListOfResources
    if resource and resource.parent and resource.parent.name and resource.parent.type:
      if resource.parent.id:
        parent_resource = self._resources_dict.get(resource.parent.id)
        if not parent_resource:
          parent_resource = resource.parent
      else:
        matched_parent_resources = self._GetResourceInfoByName(resource.parent.name,
                                                               resource.parent.type)
        if not matched_parent_resources:
            parent_resource = resource.parent
        elif len(matched_parent_resources) > 1:
          # TODO Ask the user which one should we work with or find a way to choose
          # to chose automatically
          self.logger.warning(
              'There are multiple resources with the same name')
        else:
          parent_resource = matched_parent_resources[0]

    elif resource and resource.disks:
      for disk in resource.disks:
        if disk and disk.name and disk.type:
          if disk.id:
            parent_resource = self._resources_dict.get(disk.id)
          else:
            matched_disks = self._GetResourceInfoByName(disk.name,
                                                        disk.type)
            if not matched_disks:
              parent_resource = disk
            elif len(matched_disks) > 1:
              # TODO Ask the user which one should we work with or find a way to choose
              # to chose automatically
              self.logger.warning(
                  'There are multiple resources with the same name')
            else:
              parent_resource = matched_disks[0]

    if parent_resource:
      if parent_resource.IsDeleted() and self._mode == 'online':
        found_resource = self._SearchForDeletedResource(
            parent_resource, resource.creation_timestamp, 'backword')
        if found_resource:
          if found_resource.id:
            self._resources_dict[found_resource.id] = found_resource
          parent_resource = found_resource

      # Recursively obtain parents for each resource in the chain
      parent_resource.parent = self._GetResourceParent(parent_resource)

    # Return the resource with all the parent chain filled
    return parent_resource

  def _GetResourceChildren(self, parent_resource: Resource) -> List[Resource]:
    """Return the children of a given resource.

    Args:
      parent_resource: The resource object to get children of

    Returns:
      List of resource objects
    """

    if not parent_resource:
      return None

    children_resources = []

    for child in parent_resource.children:
      children_resources.append(child)

    # Check if the child_resource has the same parent name as the resource we want
    # to obtain the children for. If true then add the child_resource to the
    # children_resources and recursively obtain children for the tempResource
    # itself.
    for id, child_resource in self._resources_dict.items():

      # skip id the the if of the current resource returned by the loop is the
      # same as the resource we want to find the children for
      if id == parent_resource.id:
        continue

      # Check if the parent name of the current resource returned by the loop
      # is the same as the name of the resource we want to find the children for
      if child_resource and child_resource.parent and child_resource.parent.name == parent_resource.name:
        child_resource.children = self._GetResourceChildren(child_resource)
        children_resources.append(child_resource)

      # If the current resource returned by the loop has disks
      # (gce_instance, gce_instance_template, gce_machine_image)
      elif child_resource and child_resource.disks:
        for disk in child_resource.disks:
          #if disk.parent and not disk.id:
            #print(f'parent_resource: {parent_resource.name}  child_resource: {child_resource.name} child_disk_resource: {disk.name} child_disk_parent_resource: {disk.parent.name}')

          if disk and not disk.id and disk.parent and disk.parent.name == parent_resource.name:
            print(f'adding {child_resource.name} {child_resource.type}')
            # When parsing log files in offline mode, some disks info will be
            # available but still not updated under the (gce_instance, gce_instance_template, gce_machine_image)
            matched_resources = self._GetResourceInfoByName(
                disk.name, disk.type)
            if matched_resources:
              disk = matched_resources[0]
              children_resources.append(child_resource)
              print(f'found {matched_resources}')
            else:
              # Logs don't have a separate log entry for default disks created
              # when creating instances. There for we add the disk as is here
              # with it's missing information
              children_resources.append(disk)
              disk.children.append(child_resource)
          elif disk and disk.name == parent_resource.name:

            print(
                f'adding 2 {disk.name} {child_resource.name} {child_resource.type} to {parent_resource.name}')
            children_resources.append(child_resource)

    return children_resources

  def _GetResourceInfoByName(self, resource_name: str, resource_type: str) -> List[Resource]:
    """Search for a resource by name and type in the _resource_dict dictionary.

    Args:
      resource_name: Resource name.
      resource_type: Resource type (currently supported types: gce_instance,
        gce_disk, gce_image, gce_machine_image, gce_instance_template, gce_snapshot)

    Return:
      List of Resource object that match the name and type or None if a matching
      resource is not found

    """

    resources = []

    # Search for the resource with the same name and type in the parsed logs.
    for resource in self._resources_dict.values():
      if resource and resource.name == resource_name and resource.type == resource_type:
        resources.append(resource)

    return resources

  def _GetLogMessages(self, project_id: str, start_timestamp: str, end_timestamp: str, resource_id: Optional[str] = None):
    """ Acquire log messages from GCP logs for a specific project id and between
        a start and end timestamps.

        Args:
         project_id: Project id from which we are going to obtain the logs.
         start_timestamp: Retrive logs starting at this timestamp.
         end_timestamp: Retrive logs ending at this timestamp.
    """

    gcl = GoogleCloudLog(project_ids=[project_id])

    filter = f'resource.type = ("gce_instance" OR "api" OR "gce_disk" OR "gce_image" OR "gce_instance_template" OR "gce_snapshot") \
    AND logName = "projects/{project_id}/logs/cloudaudit.googleapis.com%2Factivity" \
    AND operation.first = "true" \
    AND timestamp >= "{start_timestamp}" \
    AND timestamp <= "{end_timestamp}" \
    AND severity=NOTICE \
    AND protoPayload.methodName : ("insert" OR "create" OR "delete")'

    if resource_id:
      filter = filter + \
          f' AND (resource.labels.instance_id="{resource_id}" OR resource.labels.image_id="{resource_id}")'

    log_messages = gcl.ExecuteQuery(qfilter=[filter])

    return log_messages

  def _ParseLogMessagesFromFileContainer(self, file_container: containers.File) -> None:
    """Parse GCP Cloud log messages supplied in the file container and fill
        the self._resource_dict with the result

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

  def _ParseLogMessages(self, log_messages: list[str]) -> None:
    """Parse GCP Cloud log messages and fill
        the self._resource_dict with the result

    Args:
      log_messages: list of log messages
    """

    for log_message in log_messages:

      proto_payload = log_message.get('protoPayload')

      if not proto_payload:
        continue

      request = proto_payload.get('request')
      response = proto_payload.get('response')
      if not request or not response:
        print('Request or Response missing')
        continue

      log_message_type = request.get('@type').split('/')[
          -1]  # Example: @type: "type.googleapis.com/compute.instances.insert"

      # Parse logs for supported resource types
      if log_message_type.startswith(('compute.instances', 'compute.disks',
                                      'compute.machineImages', 'compute.image', 'compute.instanceTemplates', 'compute.snapshots')):

        # Check if a resource with the same ID already exist in the
        # self._resources_dict dictionary
        if self._resources_dict.get(response.get('targetId')):
          resource = self._resources_dict.get(response.get('targetId'))
        else:
          resource = Resource()
          resource.id = response.get('targetId')
          resource.status = response.get('status')

          # compute.disks.createSnapshot is a special case where the
          # "resourceName" is just the name and not the full name with the
          # project, zone, type and name
          if log_message_type.startswith('compute.disks.createSnapshot'):
            # TODO Build the resource_name in the Resource class.
            resource.name = request.get('name')
            resource.type = log_message.get('resource', {}).get('type')
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
        self.logger.warn(f'Type {log_message_type} not supported')
        resource = None

      if resource and resource.id:
        self._resources_dict[resource.id] = resource

  def _ParseInsertLogMessage(self, resource: Resource, request: dict, response: dict) -> Resource:
    """Parse a GCP log message where the operation is insert or create.

    Args:
      resource: Resource object to update with parsed information
      request: Resquest portion of the log message
      response: Response portion of the log message

    Returns:
      Resource object filled with data parsed from the Log message
    """

    resource.creation_timestamp = response.get('insertTime')
    resource.created_by = response.get('user')

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
        for disk in request.get('disks'):
          diskResource = Resource()
          diskResource.name = disk.get('deviceName')
          diskResource.type = 'gce_disk'
          diskResource.zone = resource.zone
          diskResource.project_id = resource.project_id
          initialize_params = disk.get('initializeParams')
          if initialize_params:

            if 'sourceImage' in initialize_params:
              if not diskResource.parent:
                diskResource.parent = Resource()
              diskResource.parent.resource_name = initialize_params.get(
                  'sourceImage')

            elif 'sourceSnapshot' in initialize_params:
              if not diskResource.parent:
                diskResource.parent = Resource()
              diskResource.parent.resource_name = initialize_params.get(
                  'sourceSnapshot')

          elif 'source' in disk:  # cloned disk falls here
            if not diskResource.parent:
              diskResource.parent = Resource()
            diskResource.parent.resource_name = disk.get('source')

          if diskResource:
            matched_resources = self._GetResourceInfoByName(
                diskResource.name, diskResource.type)
            if not matched_resources:
              #This is an exceptional case cause the logs don't have an entry
              #for disks being created automaticlay when a gce_instance is
              #created. The automatically created disk has the same name as the gce_instance
              if diskResource.name == resource.name:
                diskResource.creation_timestamp = resource.creation_timestamp
              resource.disks.append(diskResource)
              print(f'disk {diskResource.name} not found')
            else:
              resource.disks.append(
                  self._resources_dict.get(matched_resources[0].id))
              print(f'disk {matched_resources[0].name} found')

          if diskResource.parent:
            matched_resources = self._GetResourceInfoByName(
                diskResource.parent.name, diskResource.parent.type)
            if not matched_resources:
              pass
            else:
              diskResource.parent = self._resources_dict.get(
                  matched_resources[0].id)
              # self._resources_dict.get(r[0].id).children.append(diskResource)
              print(f'parent disk {matched_resources[0].name} found')

    if resource.parent:
      matched_resources = self._GetResourceInfoByName(
          resource.parent.name, resource.parent.type)
      if not matched_resources:
        pass
      else:
        resource.parent = self._resources_dict.get(matched_resources[0].id)
        # self._resources_dict.get(r[0].id).children.append(diskResource)
        print(f'parent resource {matched_resources[0].name} found')

    return resource

  def _BuildResourcesParentRelateionship(self) -> None:
    """Build parent relationship for all resources"""

    # Using resource_keys because self._resources_dict changes during the loop
    resource_keys = list(self._resources_dict.keys())
    for resource_key in resource_keys:
      resource = self._resources_dict.get(resource_key)
      resource.parent = self._GetResourceParent(resource)

  def _GetResourceInfoFromBatchHistory(self, project_id: str, zone: str, resource_name: str, resource_type: str):
    """Retrive resource information using the Cloud CAI API. The holds
      information on deleted hosts in the last 35 days.

    Args:
      project_id: Project id where the resource is located.
      zone: Zone, under the project, where the resource is located.
      resource_name: Resource name.
      resource_type: Resource type (currently supported types: gce_instance,
        gce_disk, gce_image, gce_machine_image, gce_instance_template, gce_snapshot)

    """
    client = asset_v1.AssetServiceClient()
    parent = "projects/{}".format(project_id)
    content_type = asset_v1.ContentType.RESOURCE
    read_time_window = asset_v1.TimeWindow()
    read_time_window.end_time = parser.parse("2021-11-20T00:00:00Z")
    read_time_window.start_time = parser.parse("2021-11-01T00:00:00Z")
    response = client.batch_get_assets_history(
        request={
            "parent": parent,
            "asset_names": [f'//compute.googleapis.com/projects/{project_id}/global/{resource_type}/{resource_name}'],
            "content_type": content_type,
            "read_time_window": read_time_window,
        }
    )

    for asset in response.assets:
      print(asset.deleted)
      print(asset.ListFields())
      if asset.get('deleted') and asset.get('deleted') == 'true':
        print(
            f'Asset {asset.get("asset",{}).get("name")} was deleted on {asset.get("window",{}).get("startTime")}')
      if asset.get('asset', {}).get('resource', {}).get("data", {}).get('creationTimestamp'):
        print(
            f'creation timestamp: {asset.get("asset",{}).get("resource",{}).get("data",{}).get("creationTimestamp")}')

    # print("assets: {}".format(response.assets))

  def _SearchForDeletedResource(self, resource: Resource,
                                start_timestamp: datetime, direction: str) -> Resource:
    """Search for deleted resouce in GCP Logs.

    Args:
      resource: resource to search for.
      start_timestamp: the initial point of time to start the search
      direction: whether to go backwards or forwards in time

    Retruns:
      Found resource or None
    """

    if not resource or not start_timestamp or not direction:
      return

    if resource.project_id != self._project_id:
      return

    if not self._period_covered_by_retrieved_logs.get('start'):
      self._period_covered_by_retrieved_logs['start'] = start_timestamp
    if not self._period_covered_by_retrieved_logs.get('end'):
      self._period_covered_by_retrieved_logs['end'] = start_timestamp

    if direction == 'backword':

      while start_timestamp > (datetime.now(timezone.utc) - timedelta(days=400)):

        end_timestamp = start_timestamp + timedelta(minutes=20)
        start_timestamp = start_timestamp - timedelta(days=30)

        if start_timestamp < self._period_covered_by_retrieved_logs.get('start'):
          self._period_covered_by_retrieved_logs['start'] = start_timestamp
          if end_timestamp < self._period_covered_by_retrieved_logs.get('end'):
            end_timestamp = self._period_covered_by_retrieved_logs.get('start')

        if end_timestamp > self._period_covered_by_retrieved_logs.get('end'):
          self._period_covered_by_retrieved_logs['end'] = end_timestamp
          if start_timestamp > self._period_covered_by_retrieved_logs.get('start'):
            start_timestamp = self._period_covered_by_retrieved_logs.get('end')

        else:
          continue

        print(f'Searching between {start_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} and {end_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} for {resource.name} {resource.type}')
        log_messages = self._GetLogMessages(resource.project_id, start_timestamp.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"), end_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), resource.id)
        self._ParseLogMessages(log_messages)

        matched_resource = self._GetResourceInfoByName(
            resource.name, resource.type)
        if matched_resource:
          if matched_resource[0].deletion_timestamp and matched_resource[0].creation_timestamp:
            return matched_resource[0]

    else:
      return


modules_manager.ModulesManager.RegisterModule(GCPCloudResourceTree)
