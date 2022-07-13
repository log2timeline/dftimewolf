# -*- coding: utf-8 -*-
"""Generates a GCP cloud resource tree."""

import json
import tempfile
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Dict, List, Optional, Any

from libcloudforensics.providers.gcp.internal import common as gcp_common
from libcloudforensics.providers.gcp.internal import log as gcp_log

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import state

from dftimewolf.lib.processors import gcp_cloud_resource_tree_helper as gcp_crt_helper # pylint: disable=line-too-long


class GCPCloudResourceTree(module.BaseModule):
  """GCP Cloud Resource Tree Creator.

  Attributes:
    project_id (str): Id of the project where the resource is located.
    resource_name (str): Name of the resource to build the tree for.
    resource_type (str): Resource type.
    mode (gcp_crt_helper.OperatingMode): Module operation mode
    resources_dict (Dict[str, Resource]): Dictionary of resources
    period_covered_by_retrieved_logs (Dict[str, datetime]): Dictionary of the time
        range of logs retrieved and processed

  """

  def __init__(self,
               state: state.DFTimewolfState,
               name: Optional[str] = None,
               critical: bool = True) -> None:
    """Initializes the Cloud Resource Tree Processor.

    Args:
      state: recipe state.
      name: The module's runtime name.
      critical: True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GCPCloudResourceTree, self).__init__(state,
                                               name=name,
                                               critical=critical)

    self.project_id: str = ''
    self.resource_name: str = ''
    self.resource_type: str = ''
    self.mode: gcp_crt_helper.OperatingMode = gcp_crt_helper.OperatingMode.ONLINE
    self.period_covered_by_retrieved_logs: Dict[str, datetime] = {}
    self.resources_dict: Dict[str, gcp_crt_helper.Resource] = {}

  # pylint: disable=arguments-differ
  def SetUp(self, project_id: str, resource_name: str, resource_type: str,
            mode: str) -> None:
    """Sets up the resource we want to build the tree for.

    Args:
      project_id: Project id where the resources are located.
      resource_name: Resource name.
      resource_type: Resource type (currently supported types: gce_instance,
          gce_disk, gce_image, gce_machine_image, gce_instance_template,
          gce_snapshot)
      mode: operational mode (online or offline)
    """
    self.project_id = project_id
    self.resource_name = resource_name
    self.resource_type = resource_type
    if 'offline' in mode:
      self.mode = gcp_crt_helper.OperatingMode.OFFLINE
    elif 'online' in mode:
      self.mode = gcp_crt_helper.OperatingMode.ONLINE

  def Process(self) -> None:
    """Creates the GCP Cloud Resource Tree."""
    if self.mode == gcp_crt_helper.OperatingMode.OFFLINE:
      self.logger.info('Starting module in offline mode.')
      # Get the file containers created by the previous module in the recipe
      file_containers = self.state.GetContainers(containers.File)

      # Loop over the file containers and parse the content of each to fill the
      # resources dictionary
      for file_container in file_containers:
        self.logger.info(
            f'Loading file from file system container: {file_container.path}')
        self._ParseLogMessagesFromFileContainer(file_container)

    elif self.mode == gcp_crt_helper.OperatingMode.ONLINE:
      self.logger.info('Starting module in online mode.')
      self._GetListOfResources(self.project_id)
      self._GetResourcesMetaDataFromLogs(self.project_id)

    else:
      self.PublishMessage(
          'Invalid operating mode. Supported modes are "online" or "offline"')

    self._BuildResourcesParentRelationships()

    resource = self._FindResource(self.resource_name, self.resource_type, None,
                                  self.project_id)

    if not resource:
      self.logger.error('Resource not found')
      return

    # Save resource tree to temp file
    output_file = tempfile.NamedTemporaryFile(mode='w',
                                              delete=False,
                                              encoding='utf-8',
                                              suffix='.txt')
    output_path = output_file.name

    self.PublishMessage(f'Saving resource tree to {output_path}')
    with open(output_path, 'w') as out_file:
      if resource.parent:
        out_file.write(str(resource.parent))
      else:
        out_file.write(str(resource))

    # Dump the resource tree to CLI
    if resource.parent:
      self.PublishMessage(str(resource.parent))
    else:
      self.PublishMessage(str(resource))

  def _GetListOfResources(self, project_id: str) -> None:
    """Acquires a list of resources under a project.

    Args:
      project_id: Project id to get list of resources from.
    """
    # Retrieve list of disks in a project
    self.resources_dict.update(self._RetrieveListOfDisks(project_id))

    # Retrieve list of disk images in a project
    self.resources_dict.update(self._RetrieveListOfDiskImages(project_id))

    # Retrieve list of snapshots in a project
    self.resources_dict.update(self._RetrieveListOfSnapshots(project_id))

    # Retrieve list of instances in a project
    self.resources_dict.update(self._RetrieveListOfInstances(project_id))

    # Retrieve list of instance templates in a project
    self.resources_dict.update(
        self._RetrieveListOfInstanceTemplates(project_id))

    # Retrieve list of machine images in a project
    self.resources_dict.update(self._RetrieveListOfMachineImages(project_id))

  def _GetResourcesMetaDataFromLogs(self, project_id: str) -> None:
    """Enriches resources with meta data from GCP Logs.

    Generate list of time ranges based on the creation timestamps of the
    obtained resources and query the logs for these time ranges to obtain
    additional metadata about the creation of the resources.

    Args:
      project_id: Project id to get list of resources from.
    """
    time_ranges: List[Dict[str, datetime]] = []

    all_active_resources_sorted = sorted(
        self.resources_dict.values(),
        key=lambda resource: resource.creation_timestamp)  # type: ignore

    for resource in all_active_resources_sorted:
      # Building list of timestamp ranges to query. The loop will go through the
      # resources in ascending order based on their creation timestamp
      time_range = {}
      if resource.creation_timestamp:
        # Handle first entry. Set start_timestamp and end_timestamp to the
        # resource creation_timestamp
        if len(time_ranges) == 0:
          time_range[
              'start_timestamp'] = resource.creation_timestamp - timedelta(
                  hours=1)
          time_range[
              'end_timestamp'] = resource.creation_timestamp + timedelta(
                  hours=1)
          time_ranges.append(time_range)
        else:
          # Check the time difference between the end_timestamp of the last time
          # range and the creation timestamp of the resource.
          time_diff = resource.creation_timestamp - time_ranges[-1][
              'end_timestamp']
          # To optimize calls to retrieve logs, we attempt to group resources
          # that have a creation timestamp within 30 days.
          if (time_diff.total_seconds() / 60 / 60 / 24) <= 30:
            time_range['start_timestamp'] = time_ranges[-1]['start_timestamp']
            time_range[
                'end_timestamp'] = resource.creation_timestamp + timedelta(
                    hours=1)
            time_ranges[-1] = time_range
          # Else if resource doesn't fall within 30 days, add a new time range
          # entry
          else:
            time_range[
                'start_timestamp'] = resource.creation_timestamp - timedelta(
                    hours=1)
            time_range[
                'end_timestamp'] = resource.creation_timestamp + timedelta(
                    hours=1)
            time_ranges.append(time_range)

    # Retrieve and parse logs for each of the time ranges.
    for time_range in time_ranges:
      log_messages = self._GetLogMessages(project_id,
                                          time_range['start_timestamp'],
                                          time_range['end_timestamp'])
      self._ParseLogMessages(log_messages)

  def _GetResourceParentTree(self, resource: gcp_crt_helper.Resource) -> Optional[gcp_crt_helper.Resource]:
    """Returns parent tree of a given resource.

    Args:
      resource: The resource object to get its parents.

    Returns:
      resource object
    """
    if not resource:
      return None

    parent_resource: Optional[gcp_crt_helper.Resource] = None

    # The resource should at least have the name and type of the parent
    # resource. This is filled during the parsing of log messages in
    # _ParesLogMessages() and/or _GetListOfResources
    if resource.parent and resource.parent.name and resource.parent.type:
      if resource.parent.id:
        parent_resource = self.resources_dict.get(resource.parent.id)
        # If the parent resource is deleted or it's one of the stock disk images
        # (for ex Debian), we will have the parent id but it's not in the list
        # of resources we parsed.
        if not parent_resource:
          parent_resource = resource.parent
      else:
        matched_parent_resource = self._FindResource(
            resource.parent.name, resource.parent.type, resource.parent.zone,
            resource.parent.project_id)
        if matched_parent_resource:
          parent_resource = matched_parent_resource
        else:
          parent_resource = resource.parent

    if parent_resource:
      if parent_resource.IsDeleted(
      ) and self.mode == gcp_crt_helper.OperatingMode.ONLINE and resource.creation_timestamp:
        found_resource = self._SearchForDeletedResource(
            parent_resource, resource.creation_timestamp)
        if found_resource:
          if found_resource.id:
            self.resources_dict[found_resource.id] = found_resource
          parent_resource = found_resource

      # Recursively obtain parents for each resource in the chain
      parent_resource.parent = self._GetResourceParentTree(parent_resource)
      parent_resource.children.add(resource)

    # Return the resource with all the parent chain filled
    return parent_resource

  def _FindResource(self,
                    resource_name: str,
                    resource_type: str,
                    zone: Optional[str] = None,
                    project_id: Optional[str] = None) -> Optional[gcp_crt_helper.Resource]:
    """Searches for a resource in the _resource_dict dictionary.

    Args:
      resource_name: Resource name.
      resource_type: Resource type (currently supported types: gce_instance,
        gce_disk, gce_image, gce_machine_image, gce_instance_template,
        gce_snapshot)
      zone (Optional): Zone where resource is located

    Return:
      Resource object that match the name and type or None if a matching
      resource is not found

    """
    # Search for the resource with the same name and type in the parsed logs.
    for resource in self.resources_dict.values():

      if resource.name == resource_name and resource.type == resource_type:
        # Filter list by zone if it is supplied
        if zone is not None and resource.zone != zone:
          continue
        # Check is project id match if project id was supplied as a filter
        # criteria
        if project_id is not None and resource.project_id != project_id:
          continue

        return resource

    return None

  def _GetLogMessages(
      self,
      project_id: str,
      start_timestamp: datetime,
      end_timestamp: datetime,
      resource_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Acquires log messages from GCP logs.

    Acquires log messages from GCP logs for a specific project id and time
    range.

    Args:
      project_id: Project id from which we are going to obtain the logs.
      start_timestamp: Retrieve logs starting at this timestamp.
      end_timestamp: Retrieve logs ending at this timestamp.
      resource_id: Optional resource id

    Return:
      List of log messages
    """
    if not project_id or not start_timestamp or not end_timestamp:
      return []

    gcl = gcp_log.GoogleCloudLog(project_ids=[project_id])

    if not self.period_covered_by_retrieved_logs.get(
        'start') or not self.period_covered_by_retrieved_logs.get('end'):
      self.period_covered_by_retrieved_logs['start'] = start_timestamp
      self.period_covered_by_retrieved_logs['end'] = end_timestamp
    else:
      # If the required time range is within the time range already retrieved
      # before return an empty list
      if start_timestamp >= self.period_covered_by_retrieved_logs[
          'start'] and end_timestamp <= self.period_covered_by_retrieved_logs[
              'end']:
        return []

    # Make sure we only request the period that was not retrieved before, for
    # optimization
    if start_timestamp < self.period_covered_by_retrieved_logs['start']:
      if end_timestamp < self.period_covered_by_retrieved_logs['end']:
        end_timestamp = self.period_covered_by_retrieved_logs['start']
      self.period_covered_by_retrieved_logs['start'] = start_timestamp

    if end_timestamp > self.period_covered_by_retrieved_logs['end']:
      if start_timestamp > self.period_covered_by_retrieved_logs['start']:
        start_timestamp = self.period_covered_by_retrieved_logs['end']
      self.period_covered_by_retrieved_logs['end'] = end_timestamp

    # pylint: disable=line-too-long
    self.PublishMessage(
        f'Retrieving logs from { start_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} to {end_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}.'
    )

    query_filter = f'resource.type = ("gce_instance" OR "api" OR "gce_disk" OR "gce_image" OR "gce_instance_template" OR "gce_snapshot") \
    AND logName = "projects/{project_id}/logs/cloudaudit.googleapis.com%2Factivity" \
    AND operation.first = "true" \
    AND timestamp >= "{start_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}" \
    AND timestamp <= "{end_timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}" \
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
    """Parses GCP Cloud log messages supplied in the file container.

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
    """Parses supplied GCP Cloud log messages.

    Parses supplied GCP Cloud log messages and fills self._resource_dict with
    the result.

    Args:
      log_messages: list of log messages
    """
    for log_message in log_messages:

      proto_payload: Dict[str, Any] = log_message.get('protoPayload', {})

      if not proto_payload:
        continue

      request_metadata = proto_payload.get('requestMetadata')
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

        # Check if a resource with the same ID already exist in the
        # self.resources_dict dictionary
        resource = self.resources_dict.get(response.get('targetId'))

        if not resource:
          resource = gcp_crt_helper.Resource()
          resource.id = response.get('targetId')

        # compute.disks.createSnapshot is a special case where the
        # "resourceName" is just the name and not the full name with the
        # project, zone, type and name
        if log_message_type.startswith('compute.disks.createSnapshot'):
          resource = gcp_crt_helper.Resource()
          source_disk_id = response.get('targetId')
          resource.name = request.get('name')
          # GCP Log issue, the resource.type is set to 'gce_disk' so i am
          # setting it manually to gce_snapshot
          resource.type = 'gce_snapshot'
          resource.project_id = log_message.get('resource',
                                                {}).get('labels',
                                                        {}).get('project_id')
          resource.zone = 'global'

          # For creation of a snapshot, its a special case where the targetId is
          # of the source disk and not the snapshot being created. And the
          # targetLink points to the source disk. The id of the snapshot
          # is not present in the log message.
          # We need to unset the id which was set earlier to targetId
          matched_resource = self._FindResource(resource.name, resource.type)
          if matched_resource:
            resource = matched_resource
          else:
            resource.id = source_disk_id + "-snapshot"

        else:
          resource.resource_name = resource.resource_name or proto_payload.get(
              'resourceName', '')

        # In case the message is an insert message
        if log_message_type.endswith('insert') or log_message_type.endswith(
            'createSnapshot'):
          if request_metadata:
            resource.creator_ip_address = request_metadata.get('callerIp')
            resource.creator_useragent = request_metadata.get(
                'callerSuppliedUserAgent')
          self._ParseInsertLogMessage(resource, request, response)

        elif log_message_type.endswith('delete'):
          resource.deletion_timestamp = response.get('insertTime')
          resource.deleted_by = response.get('user')
          if request_metadata:
            resource.deleter_ip_address = request_metadata.get('callerIp')
            resource.deleter_useragent = request_metadata.get(
                'callerSuppliedUserAgent')

      else:
        self.PublishMessage(f'Type {log_message_type} not supported')
        resource = None

      if resource:
        if resource.id:
          self.resources_dict[resource.id] = resource

  def _ParseInsertLogMessage(self, resource: gcp_crt_helper.Resource, request: Dict[str, Any],
                             response: Dict[str, Any]) -> None:
    """Parses a GCP log message where the operation is insert or create.

    Args:
      resource: Resource object to update with parsed information.
      request: Request portion of the log message.
      response: Response portion of the log message.
    """
    resource.creation_timestamp = response.get('insertTime')
    resource.created_by = response.get('user', '')

    if 'sourceDisk' in request:
      if not resource.parent:
        resource.parent = gcp_crt_helper.Resource()
        resource.parent.resource_name = request.get('sourceDisk', '')

    # When creating machine image from an instance
    elif 'sourceInstance' in request:
      if not resource.parent:
        resource.parent = gcp_crt_helper.Resource()
        resource.parent.resource_name = request.get('sourceInstance', '')

    # When creating a disk image from another disk
    elif 'sourceSnapshot' in request:
      if not resource.parent:
        resource.parent = gcp_crt_helper.Resource()
        resource.parent.resource_name = request.get('sourceSnapshot', '')

    # When creating a new instance, one of
    # initializeParams.sourceImage or initializeParams.sourceSnapshot or
    # disks.source is required except for local SSD.
    if request.get('disks'):
      for disk in request.get('disks', {}):
        disk_resource = gcp_crt_helper.Resource()
        disk_resource.project_id = resource.project_id
        disk_resource.created_by = resource.created_by
        disk_resource.creator_ip_address = resource.creator_ip_address
        disk_resource.creator_useragent = resource.creator_useragent
        disk_resource.zone = resource.zone
        disk_resource.name = disk.get('deviceName')
        disk_resource.type = 'gce_disk'

        # When creating an instance from a machine image
        if 'sourceMachineImage' in request:
          disk_resource.parent = gcp_crt_helper.Resource()
          disk_resource.parent.resource_name = request.get(
              'sourceMachineImage', '')

        # Check if we already have the disk in the resources_dict. If true
        # then add it to the resource disks list and continue to next disk.
        matched_resource = self._FindResource(disk_resource.name,
                                              disk_resource.type,
                                              disk_resource.zone,
                                              disk_resource.project_id)

        # pylint: disable=line-too-long
        if matched_resource:
          matched_resource.created_by = matched_resource.created_by or resource.created_by
          matched_resource.creator_ip_address = matched_resource.creator_ip_address or resource.creator_ip_address
          matched_resource.creator_useragent = matched_resource.creator_useragent or resource.creator_useragent
          matched_resource.parent = matched_resource.parent or disk_resource.parent
          resource.disks.append(matched_resource)
          continue
        # pylint: enable=line-too-long

        initialize_params = disk.get('initializeParams')
        if initialize_params:
          # When instance is created using an existing disk image, machine image
          # or template
          if 'sourceImage' in initialize_params:
            if not disk_resource.parent:
              disk_resource.parent = gcp_crt_helper.Resource()
            disk_resource.parent.resource_name = initialize_params.get(
                'sourceImage')

          # When instance is created using an existing disk snapshot
          elif 'sourceSnapshot' in initialize_params:
            if not disk_resource.parent:
              disk_resource.parent = gcp_crt_helper.Resource()
            disk_resource.parent.resource_name = initialize_params.get(
                'sourceSnapshot')

        # When instance is created using an existing cloned disk
        elif 'source' in disk:
          if not disk_resource.parent:
            disk_resource.parent = gcp_crt_helper.Resource()
          disk_resource.parent.resource_name = disk.get('source')

        # This is an exceptional case cause the logs don't have an entry
        # for disks being created automatically when a gce_instance is
        # created. The automatically created disk has the same name as the
        # gce_instance
        if disk_resource.name == resource.name:
          disk_resource.creation_timestamp = resource.creation_timestamp
          resource.parent = disk_resource
          disk_resource.id = resource.id + '-disk'

        resource.disks.append(disk_resource)

        if disk_resource.parent and not disk_resource.parent.id:
          matched_resource = self._FindResource(
              disk_resource.parent.name, disk_resource.parent.type,
              disk_resource.parent.zone, disk_resource.parent.project_id)
          if matched_resource:
            disk_resource.parent = matched_resource

        if disk_resource and not resource.parent:
          resource.parent = disk_resource

        if disk_resource.id:
          self.resources_dict[disk_resource.id] = disk_resource

    if resource.parent and not resource.parent.id:
      matched_resource = self._FindResource(resource.parent.name,
                                            resource.parent.type,
                                            resource.parent.zone,
                                            resource.parent.project_id)
      if matched_resource:
        resource.parent = matched_resource

  def _BuildResourcesParentRelationships(self) -> None:
    """Builds parent relationship for all resources."""
    # Using resource_keys because self.resources_dict changes during the loop
    resource_keys = list(self.resources_dict.keys())
    for resource_key in resource_keys:
      resource = self.resources_dict.get(resource_key)
      if resource:
        resource.parent = self._GetResourceParentTree(resource)

  def _SearchForDeletedResource(
      self, resource: gcp_crt_helper.Resource,
      start_timestamp: datetime) -> Optional[gcp_crt_helper.Resource]:
    """Searches for deleted resource in GCP Logs.

    Args:
      resource: resource to search for.
      start_timestamp: the initial point of time to start the search

    Return:
      Found resource or None
    """
    if not resource or not start_timestamp:
      return None

    if resource.project_id != self.project_id:
      return None

    while start_timestamp > (datetime.now(timezone.utc) - timedelta(days=400)):

      end_timestamp = start_timestamp + timedelta(minutes=20)
      start_timestamp = start_timestamp - timedelta(days=30)

      log_messages = self._GetLogMessages(resource.project_id, start_timestamp,
                                          end_timestamp, resource.id)
      self._ParseLogMessages(log_messages)

      matched_resource = self._FindResource(resource.name, resource.type)
      if matched_resource:
        if matched_resource.deletion_timestamp and matched_resource.creation_timestamp:  # pylint: disable=line-too-long
          return matched_resource

    return None

  def _RetrieveListOfDisks(self, project_id: str) -> Dict[str, gcp_crt_helper.Resource]:
    """Retrieves list of disks in a project.

    Args:
      project_id: Project Id to retrieve the list of disks for

    Returns:
      Dict of disks
    """
    result: Dict[str, gcp_crt_helper.Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = gcp_common.CreateService('compute', 'beta')

    request = compute_api_client.disks().aggregatedList(project=project_id)  # pylint: disable=no-member

    while request is not None:
      response = request.execute()

      for zone in response.get('items',{}).values():

        for disk in zone.get('disks', {}):
          resource = gcp_crt_helper.Resource()
          resource.id = disk.get('id')
          resource.resource_name = disk.get('selfLink')
          resource.creation_timestamp = disk.get('creationTimestamp')
          if disk.get('sourceDisk'):
            resource.parent = gcp_crt_helper.Resource()
            resource.parent.resource_name = disk.get('sourceDisk')
            resource.parent.id = disk.get('sourceDiskId')
          elif disk.get('sourceSnapshot'):
            resource.parent = gcp_crt_helper.Resource()
            resource.parent.resource_name = disk.get('sourceSnapshot')
            resource.parent.id = disk.get('sourceSnapshotId')
          elif disk.get('sourceImage'):
            resource.parent = gcp_crt_helper.Resource()
            resource.parent.resource_name = disk.get('sourceImage')
            resource.parent.id = disk.get('sourceImageId')

          result[resource.id] = resource

      # pylint: disable=no-member
      request = compute_api_client.disks().aggregatedList_next(
          previous_request=request, previous_response=response)

    return result

  def _RetrieveListOfDiskImages(self, project_id: str) -> Dict[str, gcp_crt_helper.Resource]:
    """Retrieves list of disk images in a project.

    Args:
      project_id: Project Id to retrieve the list of disk images for

    Return:
      Dict of disk images
    """
    result: Dict[str, gcp_crt_helper.Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = gcp_common.CreateService('compute', 'beta')

    # Disk images are not tied to a zone, so there is no aggregatedList
    request = compute_api_client.images().list(project=project_id)  # pylint: disable=no-member

    while request is not None:
      response = request.execute()

      if response:
        for image in response.get('items', {}):
          resource = gcp_crt_helper.Resource()
          resource.id = image.get('id')
          resource.resource_name = image.get('selfLink')
          resource.creation_timestamp = image.get('creationTimestamp')
          if image.get('sourceDisk'):
            resource.parent = gcp_crt_helper.Resource()
            resource.parent.resource_name = image.get('sourceDisk')
            resource.parent.id = image.get('sourceDiskId')
          elif image.get('sourceSnapshot'):
            resource.parent = gcp_crt_helper.Resource()
            resource.parent.resource_name = image.get('sourceSnapshot')
            resource.parent.id = image.get('sourceSnapshotId')

          result[resource.id] = resource

      # pylint: disable=no-member
      request = compute_api_client.images().list_next(
          previous_request=request, previous_response=response)

    return result

  def _RetrieveListOfSnapshots(self, project_id: str) -> Dict[str, gcp_crt_helper.Resource]:
    """Retrieves list of snapshots in a project.

    Args:
      project_id: Project Id to retrieve the list of snapshots for

    Returns:
      Dict of snapshots
    """
    result: Dict[str, gcp_crt_helper.Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = gcp_common.CreateService('compute', 'beta')

    request = compute_api_client.snapshots().list(project=project_id)  # pylint: disable=no-member

    while request is not None:
      response = request.execute()

      if response:
        for snapshot in response.get('items', {}):
          resource = gcp_crt_helper.Resource()
          resource.id = snapshot.get('id')
          resource.resource_name = snapshot.get('selfLink')
          resource.creation_timestamp = snapshot.get('creationTimestamp')
          if snapshot.get('sourceDisk'):
            resource.parent = gcp_crt_helper.Resource()
            resource.parent.resource_name = snapshot.get('sourceDisk')
            resource.parent.id = snapshot.get('sourceDiskId')

          result[resource.id] = resource

      # pylint: disable=no-member
      request = compute_api_client.snapshots().list_next(
          previous_request=request, previous_response=response)

    return result

  def _RetrieveListOfInstances(self, project_id: str) -> Dict[str, gcp_crt_helper.Resource]:
    """Retrieves list of instances in a project.

    Args:
      project_id: Project Id to retrieve the list of instances for

    Returns:
      Dict of instances
    """
    result: Dict[str, gcp_crt_helper.Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = gcp_common.CreateService('compute', 'beta')

    request = compute_api_client.instances().aggregatedList(project=project_id)  # pylint: disable=no-member

    while request is not None:
      response = request.execute()

      for zone in response['items'].values():

        for instance in zone.get('instances', {}):
          resource = gcp_crt_helper.Resource()
          resource.id = instance.get('id')
          resource.resource_name = instance.get('selfLink')
          resource.creation_timestamp = instance.get('creationTimestamp')

          for disk in instance.get('disks', {}):
            disk_resource = gcp_crt_helper.Resource()
            # 'source' here is just the full resource name of the disk. It should
            # be present for all disks
            if disk.get('source'):
              disk_resource.resource_name = disk.get('source')
              # the disk ID is not present so we have to search for it in the
              # list of processed resources
              matched_disk = self._FindResource(disk_resource.name,
                                                disk_resource.type,
                                                disk_resource.zone,
                                                disk_resource.project_id)
              if matched_disk:
                disk_resource = matched_disk

              # Adding the instance as a child to the disk
              disk_resource.children.add(resource)

              # If the instance has a sourceMachineImage set, it means that this
              # instance is created from a Machine Image. So we add this as a
              # parent to the disk
              if (instance.get('sourceMachineImage')
                  and not disk_resource.parent):
                disk_resource.parent = gcp_crt_helper.Resource()
                disk_resource.parent.resource_name = instance.get(
                    'sourceMachineImage')

              # If the disk resource name is the same name as the instance name
              # then this disk is the one created automatically with the
              # incident so we set it as its parent. There is a exceptional case
              # here where if a disk with the same name as the instance already
              # created in the same zone, GCP will alter the default name. This
              # is not handled here yet.
              if disk_resource.name == resource.name:
                if not resource.parent:
                  resource.parent = disk_resource

              if disk_resource.id:
                self.resources_dict[disk_resource.id] = disk_resource

            resource.disks.append(disk_resource)

          result[resource.id] = resource

      # pylint: disable=no-member
      request = compute_api_client.instances().aggregatedList_next(
          previous_request=request, previous_response=response)

    return result

  def _RetrieveListOfInstanceTemplates(self,
                                      project_id: str) -> Dict[str, gcp_crt_helper.Resource]:
    """Retrieves list of instance templates in a project.

    Args:
      project_id: Project Id to retrieve the list of instance templates for

    Returns:
      Dict of instance templates
    """
    result: Dict[str, gcp_crt_helper.Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = gcp_common.CreateService('compute', 'beta')

    # Retrieve list of instance templates in a project
    request = compute_api_client.instanceTemplates().list(project=project_id)  # pylint: disable=no-member

    while request is not None:
      response = request.execute()

      if response:
        for instance_template in response.get('items', {}):
          resource = gcp_crt_helper.Resource()
          resource.id = instance_template.get('id')
          resource.resource_name = instance_template.get('selfLink')
          resource.creation_timestamp = instance_template.get(
              'creationTimestamp')

          for disk in instance_template.get('properties', {}).get('disks', {}):
            disk_resource = gcp_crt_helper.Resource()
            if disk.get('source'):
              disk_resource.resource_name = disk.get('source')
              # the disk ID is not present so we have to search for it in the
              # list of processed resources
              matched_disk = self._FindResource(disk_resource.name,
                                                disk_resource.type,
                                                disk_resource.zone,
                                                disk_resource.project_id)
              if matched_disk:
                disk_resource = matched_disk

              # Adding the instance as a child to the disk
              disk_resource.children.add(resource)
            elif disk.get('deviceName'):
              disk_resource.name = disk.get('deviceName')
              disk_resource.type = 'gce_disk'
              # the disk ID is not present so we have to search for it in the
              # list of processed resources
              matched_disk = self._FindResource(disk_resource.name,
                                                disk_resource.type)
              if matched_disk:
                disk_resource = matched_disk

              # Adding the instance as a child to the disk
              disk_resource.children.add(resource)

              if disk.get('initializeParams'):
                if disk.get('initializeParams').get('sourceImage'):
                  disk_resource.parent = gcp_crt_helper.Resource()
                  disk_resource.parent.resource_name = disk.get(
                      'initializeParams').get('sourceImage')

            # If the disk resource name is the same name as the instance name
            # then this disk is the one created automatically with the
            # incident so we set it as its parent. There is a exceptional case
            # here where if a disk with the same name as the instance already
            # created in the same zone, GCP will alter the default name. This
            # is not handled here yet.
            if disk_resource.name == resource.name:
              if not resource.parent:
                resource.parent = disk_resource

            if disk_resource.id:
              self.resources_dict[disk_resource.id] = disk_resource

            resource.disks.append(disk_resource)

          result[resource.id] = resource

      # pylint: disable=no-member
      request = compute_api_client.instanceTemplates().list_next(
          previous_request=request, previous_response=response)

    return result

  def _RetrieveListOfMachineImages(self,
                                   project_id: str) -> Dict[str, gcp_crt_helper.Resource]:
    """Retrieves list of machine images in a project.

    Args:
      project_id: Project Id to retrieve the list of machine images for

    Returns:
      Dict of machine images
    """
    result: Dict[str, gcp_crt_helper.Resource] = {}

    # Using beta version of the API because v1 did not have important
    # information when creating this script
    compute_api_client = gcp_common.CreateService('compute', 'beta')

    request = compute_api_client.machineImages().list(project=project_id)  # pylint: disable=no-member

    while request is not None:
      response = request.execute()

      if response:
        for machine_image in response.get('items', {}):
          resource = gcp_crt_helper.Resource()
          resource.id = machine_image.get('id')
          resource.resource_name = machine_image.get('selfLink')
          resource.creation_timestamp = machine_image.get('creationTimestamp')

          if machine_image.get('sourceInstance'):
            resource.parent = gcp_crt_helper.Resource()
            resource.parent.resource_name = machine_image.get('sourceInstance')
            matched_resource_parent = self._FindResource(
                resource.parent.name, resource.parent.type,
                resource.parent.zone, resource.parent.project_id)
            if matched_resource_parent:
              resource.parent = matched_resource_parent

          result[resource.id] = resource

      # pylint: disable=no-member
      request = compute_api_client.machineImages().list_next(
          previous_request=request, previous_response=response)

    return result


modules_manager.ModulesManager.RegisterModule(GCPCloudResourceTree)
