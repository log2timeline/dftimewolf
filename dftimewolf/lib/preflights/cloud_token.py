"""Checks for proper authentication to Cloud platforms."""

import shutil
import subprocess

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class GCPTokenCheck(module.PreflightModule):
  """Checks for GCP authentication."""

  def SetUp(self, project_name):
    """Runs gcloud to make sure we can authenticate to GCP APIs.

    Args:
      project_name(string): the project we want to connect to.
    """

    gcloud_path = shutil.which('gcloud')
    if not gcloud_path:
      self.ModuleError(
          'Could not find path to gcloud tool. Please install gcloud SDK, as it '
          'required to authenticate to GCP')
    try:
      subprocess.check_output(
          [gcloud_path, 'auth', 'application-default', 'print-access-token', '--project', project_name])  # pylint: disable=line-too-long
    except subprocess.CalledProcessError:
      self.ModuleError(
          'Your GCP application credentials are invalid. Please run '
          'gcloud auth application-default login')


modules_manager.ModulesManager.RegisterModule(GCPTokenCheck)
