"""Checks for proper authentication to Cloud platforms."""

import shutil
import subprocess

from boto3.session import Session as BotoSession
from botocore import exceptions as boto_exceptions

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class GCPTokenCheck(module.PreflightModule):
  """Checks for GCP authentication."""

  def SetUp(self, project_name):  # pylint: disable=arguments-differ
    """Runs gcloud to make sure we can authenticate to GCP APIs.

    Args:
      project_name(string): the project we want to connect to.
    """

    gcloud_path = shutil.which('gcloud')
    if not gcloud_path:
      self.ModuleError(
          'Could not find path to gcloud tool. Please install gcloud SDK, as it'
          'is required to authenticate to GCP', critical=True)
    try:
      subprocess.check_output(
          [gcloud_path, 'auth', 'application-default', 'print-access-token', '--project', project_name])  # pylint: disable=line-too-long
    except subprocess.CalledProcessError:
      self.ModuleError(
          'Your GCP application credentials are invalid. Please run '
          'gcloud auth application-default login', critical=True)

  def Process(self):
    """Processes input and builds the module's output attribute."""

  def CleanUp(self):
    """Carries out optional cleanup actions at the end of the recipe run."""


class AWSAccountCheck(module.PreflightModule):
  """Checks for AWS authentication."""

  def SetUp(self, profile_name=None):  # pylint: disable=arguments-differ
    """Runs a boto3 check to ensure AWS authentication is configured

    Args:
      profile_name (str): Optional. The profile to test.
    """

    try:
      session = BotoSession(profile_name=profile_name)
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

  def Process(self):
    """Processes input and builds the module's output attribute."""

  def CleanUp(self):
    """Carries out optional cleanup actions at the end of the recipe run."""


modules_manager.ModulesManager.RegisterModules([
  GCPTokenCheck,
  AWSAccountCheck])
