# -*- coding: utf-8 -*-
"""Create images in GCE from image files in GCS."""

import random
import re
import time
from typing import Any, Optional, Type

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal import common
from googleapiclient.errors import HttpError
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


IMAGE_BUILD_ROLE_NAME = 'image_build_role_{0:d}'.format(
    random.randint(10**(4),(10**5)-1))
REQUIRED_PERMS = [
  'compute.disks.create',
  'compute.disks.delete',
  'compute.disks.get',
  'compute.disks.list',
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
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initialises creating images in GCE from image files in GCS.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GCSToGCEImage, self).__init__(
        state, name=name, critical=critical)
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
        self.state.StoreContainer(containers.GCSObject(obj))

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

      self.logger.info("Pausing 30 seconds to allow permissions to propagate")
      time.sleep(30) # Leave some time for permissions to propagate
    except HttpError as exception:
      # IAM service raises googleapiclient.errors.HttpError
      self.logger.critical(str(exception))
      self.ModuleError(str(exception), critical=True)

  def Process(self, container: containers.GCSObject) -> None:
    """Creates a GCE image from an image in GCS.

    Args:
      container (containers.GCSObject): The conatiner to process.
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

    self.state.StoreContainer(containers.GCEImage(image.name))

  def PostProcess(self) -> None:
    """Cleanup IAM after the fact.

    Raises:
      errors.DFTimewolfError: For any failures calling the IAM APIs.
    """
    try:
      self._DeleteRole(self.role_name)
    except HttpError as exception:
      # IAM service raises googleapiclient.errors.HttpError
      self.logger.critical(str(exception))
      self.ModuleError(str(exception), critical=True)

  def _GetRoleInfo(self) -> Any:
    """Retrieve some role information for the account.

    Returns:
      A Dict containing the role information.
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

    Returns (str):
      The name of the role.
    Raises:
      googleapiclient.errors.HttpError: On IAM API errors."""
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
      googleapiclient.errors.HttpError: On IAM API errors."""
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

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.GCSObject

  def GetThreadPoolSize(self) -> int:
    return 10

  def PreSetUp(self) -> None:
    pass

  def PostSetUp(self) -> None:
    pass


modules_manager.ModulesManager.RegisterModule(GCSToGCEImage)
