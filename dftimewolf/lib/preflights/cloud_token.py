"""Checks for proper authentication to Cloud platforms."""

import shutil
import subprocess

from boto3 import session as boto_session
from botocore import exceptions as boto_exceptions

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class GCPTokenCheck(module.PreflightModule):
  """Checks for GCP authentication."""

  # pylint: disable=arguments-differ
  def SetUp(self, project_name: str) -> None:
    """Runs gcloud to make sure we can authenticate to GCP APIs.

    Args:
      project_name (str): the project we want to connect to.
    """

    if not project_name:
      return

    gcloud_path = shutil.which('gcloud')
    if gcloud_path is None:
      self.ModuleError(
          'Could not find path to gcloud tool. Please install gcloud SDK, as it'
          'is required to authenticate to GCP', critical=True)
      return  # required for type checker to know we're bailing
    try:
      subprocess.check_output(
          [gcloud_path,
          'auth',
          'application-default',
          'print-access-token',
          '--project',
          project_name])
    except subprocess.CalledProcessError:
      self.ModuleError(
          'Your GCP application credentials are invalid. Please run '
          'gcloud auth application-default login', critical=True)

  def Process(self) -> None:
    """Processes input and builds the module's output attribute."""

  def CleanUp(self) -> None:
    """Carries out optional cleanup actions at the end of the recipe run."""


class AWSAccountCheck(module.PreflightModule):
  """Checks for AWS authentication."""

  def SetUp(self, profile_name: str='') -> None:  # pylint: disable=arguments-differ
    """Tests that AWS authentication is configured by calling the
    GetCallerIdentity action on the AWS Security Token Service (STS) API.

    Args:
      profile_name (str): Optional. The profile to test. If this parameter
        is not provided the default profile (as resolved by boto3) will be
        checked.
    """

    try:
      session = boto_session.Session(profile_name=profile_name)
      client = session.client('sts')
      client.get_caller_identity()
    except boto_exceptions.ProfileNotFound:
      self.ModuleError(
          'Profile not found, see '
          'https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#configuration', # pylint: disable=line-too-long
          critical=True)
    except boto_exceptions.NoCredentialsError:
      self.ModuleError(
          'AWS authentication is not configured, see '
          'https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#configuration', # pylint: disable=line-too-long
          critical=True)

  def Process(self) -> None:
    """Processes input and builds the module's output attribute."""

  def CleanUp(self) -> None:
    """Carries out optional cleanup actions at the end of the recipe run."""


modules_manager.ModulesManager.RegisterModules([
  GCPTokenCheck,
  AWSAccountCheck])
