# -*- coding: utf-8 -*-
"""Create images in GCE from image files in GCS."""

import random
import re
import time
from typing import Any, Callable, Type

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import common
from googleapiclient.errors import HttpError
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import cache
from dftimewolf.lib import telemetry
from dftimewolf.lib.containers import manager as container_manager


IMAGE_BUILD_ROLE_NAME = 'image_build_role_{0:d}'.format(
    random.randint(10**(4),(10**5)-1))
REQUIRED_PERMS = [
  'compute.disks.create',
  'compute.disks.delete',
  'compute.disks.get',
  'compute.disks.list',
  'compute.disks.setLabels',
  'compute.disks.use',
  'compute.disks.use',
  'compute.disks.use',
  'compute.disks.useReadOnly',
  'compute.globalOperations.get',
  'compute.images.create',
  'compute.images.get',
  'compute.images.setLabels',
  'compute.instances.create',
  'compute.instances.delete',
  'compute.instances.get',
  'compute.instances.getSerialPortOutput',
  'compute.instances.list',
  'compute.instances.setLabels',
  'compute.instances.setMetadata',
  'compute.instances.setServiceAccount',
  'compute.machineTypes.list',
  'compute.networks.get',
  'compute.networks.list',
  'compute.projects.get',
  'compute.subnetworks.use',
  'compute.subnetworks.useExternalIp',
  'compute.zoneOperations.get',
  'compute.zones.list']


class GCSToGCEImage(module.ThreadAwareModule):
  """Initialises creating images in GCE from image files in GCS."""

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initialises creating images in GCE from image files in GCS.

    Args:
      name: The modules runtime name.
      container_manager_: A common container manager object.
      cache_: A common DFTWCache object.
      telemetry_: A common telemetry collector object.
      publish_message_callback: A callback to send modules messages to.
    """
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)
    self.dest_project_name: str = ''
    self.dest_project: gcp_project.GoogleCloudProject = ''
    self.iam_service: Any = None
    self.role_name = ''

  # pylint: disable=arguments-differ
  def SetUp(self,
      dest_project: str,
      source_objects: str = '') -> None:
    """SetUp for creating images in GCE from image files in GCS.

    GCS objects to use are sourced from either the state, or passed in here.
    Args:
      dest_project (str): The destination GCP project.
      source_objects (str): Comma separated list of objects in GCS. Each
        should be of the form 'gs://bucket-name/path/to/image.bin'
    """
    self.dest_project_name = dest_project
    self.dest_project = gcp_project.GoogleCloudProject(
        self.dest_project_name)
    self.iam_service = common.CreateService('iam', 'v1')
    self.role_name = ''

    if source_objects:
      for obj in source_objects.split(','):
        self.StoreContainer(containers.GCSObject(obj))

  def PreProcess(self) -> None:
    """PreProcessing for the module.

    In this case, create or update the required role for image creation.

    Raises:
      errors.DFTimewolfError: For any failures calling the IAM APIs.
    """
    try:
      # Look for the role. If it exists, check if it is in a deleted state.
      role = self._GetRoleInfo()
      if role is None:
        # Create role
        self.logger.info(
            'Creating IAM role {0:s}'.format(IMAGE_BUILD_ROLE_NAME))
        self.role_name = self._CreateRoleForCloudBuild()
      elif role.get('deleted'):
        # Undelete
        self.logger.info(
            'Undeleting existing IAM role {0:s}'.format(IMAGE_BUILD_ROLE_NAME))
        self.role_name = self._UndeleteRole()
      else:
        # Use existing
        self.logger.info(
            'Using existing IAM role {0:s}'.format(IMAGE_BUILD_ROLE_NAME))
        self.role_name = role['name']

      self.logger.info(
          'Applying permissions for role {0:s}'.format(IMAGE_BUILD_ROLE_NAME))

      # Apply the permissions
      self._UpdateRolePermissions(self.role_name)

      # Assign role to cloudbuild account
      self._AssignRolesToCloudBuild(self.role_name)

      self.logger.debug("Pausing 30 seconds to allow permissions to propagate")
      time.sleep(30)
    except HttpError as exception:
      # IAM service raises googleapiclient.errors.HttpError
      self.ModuleError(str(exception), critical=True)

  def Process(self, container: containers.GCSObject
              ) -> None:  # pytype: disable=signature-mismatch
    """Creates a GCE image from an image in GCS.

    Args:
      container (containers.GCSObject): The container to process.
    """
    # Because this comes from a GCSObject container,
    # it should always be prefixed by gs:// - remove that.
    name = container.path[5:]
    name = re.sub(r'^.+?/', '', name)
    name = re.sub(r'[^-a-z0-9]', '-', name)

    image = self.dest_project.compute.ImportImageFromStorage(
        container.path,
        bootable = False,
        guest_environment = False,
        image_name = name)

    self.StoreContainer(
        containers.GCEImage(image.name, self.dest_project_name))

  def PostProcess(self) -> None:
    """Cleanup IAM after the fact.

    Raises:
      errors.DFTimewolfError: For any failures calling the IAM APIs.
    """
    try:
      self._DeleteRole(self.role_name)
    except HttpError as exception:
      # IAM service raises googleapiclient.errors.HttpError
      self.ModuleError(str(exception), critical=True)

  def _GetRoleInfo(self) -> Any:
    """Retrieve role information from the account for the image builder role.

    Returns:
      A Dict containing the role information, or None if the role does not
        exist.
    Raises:
      googleapiclient.errors.HttpError: On IAM API errors."""
    request = self.iam_service.roles().list( #pylint: disable=no-member
        parent='projects/' + self.dest_project_name,
        showDeleted=True)
    while True:
      response = request.execute()
      for role in response.get('roles', []):
        if role['name'] == 'projects/{0:s}/roles/{1:s}'.format(
            self.dest_project_name, IMAGE_BUILD_ROLE_NAME):
          return role

      request = self.iam_service.roles().list_next( #pylint: disable=no-member
          previous_request=request,
          previous_response=response)
      if request is None:
        break

    return None

  def _CreateRoleForCloudBuild(self) -> str:
    """Creates a role for CloudBuild.

    ImportImageFromStorage uses CloudBuild, which creates an image from the disk
    image in GCS.

    Returns:
      The name of the role.

    Raises:
      googleapiclient.errors.HttpError: On IAM API errors.
    """
    role = self.iam_service.projects().roles().create(#pylint: disable=no-member
        parent='projects/' + self.dest_project_name,
        body={
            'roleId': IMAGE_BUILD_ROLE_NAME,
            'role': {
                'title': IMAGE_BUILD_ROLE_NAME,
                'description': IMAGE_BUILD_ROLE_NAME,
                'includedPermissions': []
            }
        }).execute()

    return str(role['name'])

  # TODO(ramoj) - Make sure this gets tested?
  def _UpdateRolePermissions(self, role_name: str) -> None:
    """Assign required permissions to the role.

    Args:
      role_name (str): The role name.

    Raises:
      googleapiclient.errors.HttpError: On IAM API errors."""
    role = self.iam_service.projects().roles().get(name = role_name).execute() #pylint: disable=no-member

    perms = REQUIRED_PERMS + role.get('includedPermissions', [])

    role = self.iam_service.projects().roles().patch( #pylint: disable=no-member
        name = role_name,
        body={
            'title': role['title'],
            'description': role['description'],
            'includedPermissions': perms,
        }).execute()

  def _UndeleteRole(self) -> str:
    """Undelete the role.

    Raises:
      googleapiclient.errors.HttpError: On IAM API errors.

    Returns:
      The name of the role that was undeleted.
    """
    role = self.iam_service.projects().roles().undelete( #pylint: disable=no-member
       name='projects/{0:s}/roles/{1:s}'.format(
          self.dest_project_name, IMAGE_BUILD_ROLE_NAME)
       ).execute()
    return str(role['name'])

  def _AssignRolesToCloudBuild(self, role_name: str) -> None:
    """Assigns the roles required to CloudBuild.

    CloudBuild requires the permissions in REQUIRED_PERMS to be able to create
    a disk image from an image file in GCS.

    Args:
      role_name (str): The name fo the role.

    Raises:
      googleapiclient.errors.HttpError: On IAM API errors.
    """
    # Find the account
    crm = common.CreateService('cloudresourcemanager', 'v1')
    project = crm.projects().get(projectId=self.dest_project_name).execute() #pylint: disable=no-member

    # Get the existing IAM bindings
    policy = crm.projects().getIamPolicy( #pylint: disable=no-member
        resource=self.dest_project_name
    ).execute()

    # Cloudbuild needs our custom role and 'roles/iam.serviceAccountUser'
    cloudbuild_account = 'serviceAccount:{0:s}@cloudbuild.gserviceaccount.com'.\
        format(project['projectNumber'])
    for role in ['roles/iam.serviceAccountUser', role_name]:
      found = False
      for binding in policy['bindings']:
        if binding['role'] == role:
          found = True
          binding['members'].append(cloudbuild_account)
          break
      if not found:
        policy['bindings'].append({
          'role': role,
          'members': cloudbuild_account
        })

    # Compute default service account needs 'roles/storage.objectViewer'
    compute_acc = 'serviceAccount:{0:s}-compute@developer.gserviceaccount.com'.\
        format(project['projectNumber'])
    role = 'roles/storage.objectViewer'
    found = False
    for binding in policy['bindings']:
      if binding['role'] == role:
        found = True
        binding['members'].append(compute_acc)
        break
    if not found:
      policy['bindings'].append({
        'role': role,
        'members': compute_acc
      })

    crm.projects().setIamPolicy( #pylint: disable=no-member
        resource=self.dest_project_name,
        body={'policy': {'bindings': policy['bindings']}}
    ).execute()

  def _DeleteRole(self, role_name: str) -> None:
    """Delete the role after use.

    Args:
      role_name (str): The role to delete.
    Raises:
      googleapiclient.errors.HttpError: On IAM API errors."""
    self.logger.info('Deleting IAM role {0:s}'.format(IMAGE_BUILD_ROLE_NAME))
    self.iam_service.projects().roles().delete( #pylint: disable=no-member
        name = role_name).execute()

  def GetThreadOnContainerType(self) -> Type[interface.AttributeContainer]:
    return containers.GCSObject

  def GetThreadPoolSize(self) -> int:
    return 10


modules_manager.ModulesManager.RegisterModule(GCSToGCEImage)
