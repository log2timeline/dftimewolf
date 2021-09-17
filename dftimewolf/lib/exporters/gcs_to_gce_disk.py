# -*- coding: utf-8 -*-
"""Export objects from AWS S3 to a GCP GCS bucket."""

import re
from typing import Any, Optional, Type

from libcloudforensics.providers.gcp.internal import project as gcp_project
from libcloudforensics.providers.gcp.internal.compute import GoogleComputeDisk
from libcloudforensics.providers.gcp.internal import common
from libcloudforensics.errors import ResourceCreationError
from libcloudforensics.providers.utils.storage_utils import SplitStoragePath
from google.cloud.storage.client import Client as storage_client
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers, interface
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState

import json
import pprint

DISK_BUILD_ROLE_NAME = 'disk_build_role'

class GCSToGCEDisk(module.ThreadAwareModule):
  """Initialises creating disks in GCE from images in GCS.
  """

  def __init__(self,
               state: DFTimewolfState,
               name: Optional[str]=None,
               critical: bool=False) -> None:
    """Initialises creating disks in GCE from images in GCS.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GCSToGCEDisk, self).__init__(
        state, name=name, critical=critical)
    self.dest_project_name: str = ''
    self.dest_project: gcp_project.GoogleCloudProject = ''
    self.dest_region: str = ''
    self.iam_service: Any = None
    self.role_name = ''

  # pylint: disable=arguments-differ
  def SetUp(self,
      dest_project: str,
      dest_region: str,
      source_objects: str = '') -> None:
    """SetUp for creating disks in GCE from images in GCS.

    GCS objects to use are sourced from either the state, or passed in here.
    Args:
      dest_project (str): The destination GCP project.
      source_objects (str): Comma separated list of objects in GCS. Each
        should be of the form 'gs://bucket-name/path/to/image.bin'
    """
    self.dest_project_name = dest_project
    self.dest_region = dest_region
    self.dest_project = gcp_project.GoogleCloudProject(
        self.dest_project_name, self.dest_region)
    self.iam_service = common.CreateService('iam', 'v1')
    self.role_name = ''

    if source_objects:
      for obj in source_objects.split(','):
        self.state.StoreContainer(containers.GCSObject(obj))

  def PreProcess(self) -> None:
    # Cloud build service account needs 'compute.networks.get' permissions
    
    # Look for the role. If it exists, check if it is in a deleted state.
    role = self._GetRoleInfo()
    if role is None:
      # Create role
      self.logger.info('Creating IAM role {0:s}'.format(DISK_BUILD_ROLE_NAME))
      self.role_name = self._CreateRoleForCloudBuild()
    elif 'deleted' in role and role['deleted']:
      self.logger.info('Undeleting existing IAM role {0:s}'.format(DISK_BUILD_ROLE_NAME))
      self.role_name = self._UndeleteRole()
    else:
      self.logger.info('Using existing IAM role {0:s}'.format(DISK_BUILD_ROLE_NAME))
      self.role_name = role['name']

    # Assign role to cloudbuild account
    self._AssignRoleToCloudBuild(self.role_name)

  def Process(self, container: containers.GCSObject) -> None:
    return
    """Creates a GCE disk from an image in GCS."""
    compute = self.dest_project.compute

    disk = compute.ImportImageFromStorage(
        container.path,
        bootable = False,
        guest_environment = False)

    print(disk)

  def PostProcess(self) -> None:
    self._DeleteRole(self.role_name)

  def _GetRoleInfo(self) -> Any:
    request = self.iam_service.roles().list(parent='projects/' + self.dest_project_name, showDeleted=True, view='FULL')
    while True:
      response = request.execute()
      for role in response.get('roles', []):
        if role['name'] == 'projects/' + self.dest_project_name + '/roles/' + DISK_BUILD_ROLE_NAME:
          return role

      request = self.iam_service.roles().list_next(previous_request=request, previous_response=response)
      if request is None:
        break

    return None

  def _CreateRoleForCloudBuild(self) -> str:
    """Creates a role for CloudBuild, with the perms necessary for this module.
    """
    role = self.iam_service.projects().roles().create(
        parent='projects/' + self.dest_project_name,
        body={
            'roleId': DISK_BUILD_ROLE_NAME,
            'role': {
                'title': DISK_BUILD_ROLE_NAME,
                'description': DISK_BUILD_ROLE_NAME,
                'includedPermissions': [
                  'compute.networks.get'
                ]
            }
        }).execute()

    return str(role['name'])

  def _UndeleteRole(self) -> str:
    """Undelete the role."""
    role = self.iam_service.projects().roles().undelete(
       name='projects/' + self.dest_project_name + '/roles/' + DISK_BUILD_ROLE_NAME
       ).execute()
    return str(role['name'])

  def _AssignRoleToCloudBuild(self, role_name: str) -> None:
    # Find the account
    crm = common.CreateService('cloudresourcemanager', 'v1')
    response = crm.projects().get(projectId=self.dest_project_name).execute()
    account = 'serviceAccount:{0:s}@cloudbuild.gserviceaccount.com'.format(response['projectNumber'])

    # Get the existing IAM bindings
    request = crm.projects().getIamPolicy(resource=self.dest_project_name)
    policy = request.execute()

    # Add in the new binding
    found = False
    for binding in policy['bindings']:
      if binding['role'] == role_name:
        if not account in binding['members']:
          binding['members'].append(account)
        found = True
    if not found:
      policy['bindings'].append({
        'role': role_name,
        'members': [account]
      })

    crm.projects().setIamPolicy(resource=self.dest_project_name, body={'policy': {'bindings': policy['bindings']}}).execute()

  def _DeleteRole(self, role_name: str) -> None:
    self.logger.info('Deleting IAM role {0:s}'.format(DISK_BUILD_ROLE_NAME))
    self.iam_service.projects().roles().delete(
        name = role_name).execute()

  @staticmethod
  def GetThreadOnContainerType() -> Type[interface.AttributeContainer]:
    return containers.GCSObject

  def GetThreadPoolSize(self) -> int:
    return 1

  def PreSetUp(self) -> None:
    pass

  def PostSetUp(self) -> None:
    pass



modules_manager.ModulesManager.RegisterModule(GCSToGCEDisk)
