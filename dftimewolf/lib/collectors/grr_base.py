"""Base GRR module class. GRR modules should extend it."""
import abc
import os
import tempfile
import time

from grr_api_client import api as grr_api
from grr_api_client import errors as grr_errors

from dftimewolf.lib import module


class GRRBaseModule(module.BaseModule):
  """Base module for GRR hunt and flow modules.

  Attributes:
    output_path (str): path to store collected artifacts.
    grr_api: GRR HTTP API client.
    grr_url: GRR HTTP URL.
    reason (str): justification for GRR access.
    approvers: list of GRR approval recipients.
  """

  _CHECK_APPROVAL_INTERVAL_SEC = 10

  def __init__(self, state, name=None, critical=False):
    """Initializes a GRR hunt or flow module.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GRRBaseModule, self).__init__(state, name=name, critical=critical)
    self.reason = None
    self.grr_api = None
    self.grr_url = None
    self.approvers = None
    self.output_path = None

  # pylint: disable=arguments-differ
  def SetUp(
      self, reason, grr_server_url, grr_username, grr_password, approvers=None,
      verify=True):
    """Initializes a GRR hunt result collector.

    Args:
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      approvers (Optional[str]): comma-separated GRR approval recipients.
      verify (Optional[bool]): True to indicate GRR server's x509 certificate
          should be verified.
    """
    grr_auth = (grr_username, grr_password)
    self.approvers = []
    if approvers:
      self.approvers = [item.strip() for item in approvers.split(',')]
    self.grr_api = grr_api.InitHttp(api_endpoint=grr_server_url,
                                    auth=grr_auth,
                                    verify=verify)
    self.grr_url = grr_server_url
    self.output_path = tempfile.mkdtemp()
    self.reason = reason

  # TODO: change object to more specific GRR type information.
  def _WrapGRRRequestWithApproval(
      self, grr_object, grr_function, *args, **kwargs):
    """Wraps a GRR request with approval.

    This method will request the approval if not yet granted.

    Args:
      grr_object (object): GRR object to create the eventual approval on.
      grr_function (function): GRR function requiring approval.
      args (list[object]): Positional arguments that are to be passed
          to `grr_function`.
      kwargs (dict[str, object]): keyword arguments that are to be passed
          to `grr_function`.

    Returns:
      object: return value of the execution of grr_function(*args, **kwargs).
    """
    approval_sent = False
    approval_url = None

    while True:
      try:
        return grr_function(*args, **kwargs)

      except grr_errors.AccessForbiddenError as exception:
        self.logger.info('No valid approval found: {0!s}'.format(exception))
        # If approval was already sent, just wait a bit more.
        if approval_sent:
          self.logger.info('Approval not yet granted, waiting {0:d}s:\n{1:s}'.
                           format(self._CHECK_APPROVAL_INTERVAL_SEC,
                                  approval_url))
          time.sleep(self._CHECK_APPROVAL_INTERVAL_SEC)
          continue

        # If no approvers were specified, abort.
        if not self.approvers:
          message = ('GRR needs approval but no approvers specified '
                     '(hint: use --approvers)')
          self.ModuleError(message, critical=True)

        # Otherwise, send a request for approval
        approval = grr_object.CreateApproval(
            reason=self.reason, notified_users=self.approvers)
        approval_sent = True
        approval_url = ('{0:s}/#/users/{1:s}/approvals/client/{2:s}/{3:s}'.
                        format(self.grr_url, os.environ['USER'],
                               approval.client_id,
                               approval.approval_id))
        self.logger.info(
            '{0!s}: approval request sent to: {1!s} (reason: {2:s})'.format(
                grr_object, self.approvers, self.reason))

  @abc.abstractmethod
  def Process(self):
    """Processes input and builds the module's output attribute.

    Modules take input information and process it into output information,
    which can in turn be ingested as input information by other modules.
    """
