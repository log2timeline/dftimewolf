"""Base GRR module class. GRR modules should extend it."""

from __future__ import print_function
from __future__ import unicode_literals

import tempfile
import time

from grr_api_client import api as grr_api
from grr_api_client import errors as grr_errors

from dftimewolf.lib.module import BaseModule

# This class does not implement process() since it is a base class.
class GRRBaseModule(BaseModule):  # pylint: disable=abstract-method
  """Base module for GRR hunt and flow modules.

  Attributes:
    output_path: Path to store collected artifacts.
    grr_api: GRR HTTP API client.
    reason: Justification for GRR access.
    approvers: list of GRR approval recipients.
  """
  _CHECK_APPROVAL_INTERVAL_SEC = 10

  def __init__(self, state):
    super(GRRBaseModule, self).__init__(state)
    self.reason = None
    self.grr_api = None
    self.approvers = None
    self.output_path = None

  # pylint: disable=arguments-differ
  def setup(self, reason, grr_server_url, grr_auth, approvers=None):
    """Initializes a GRR hunt result collector.

    Args:
      reason: justification for GRR access.
      grr_server_url: GRR server URL.
      grr_auth: Tuple containing a (username, password) combination.
      approvers: list of GRR approval recipients.
    """

    self.approvers = []
    if approvers:
      self.approvers = [item.strip() for item in approvers.strip().split(',')]
    self.grr_api = grr_api.InitHttp(api_endpoint=grr_server_url, auth=grr_auth)
    self.output_path = tempfile.mkdtemp()
    self.reason = reason

  def _check_approval_wrapper(self, grr_object, grr_function, *args, **kwargs):
    """Wraps a call to GRR functions checking for approval.

    Args:
      grr_object: the GRR object to create the eventual approval on.
      grr_function: The GRR function requiring approval.
      *args: Positional arguments that are to be passed to `grr_function`.
      **kwargs: Keyword arguments that are to be passed to `grr_function`.

    Returns:
      The return value of the execution of grr_function(*args, **kwargs).
    """
    approval_sent = False

    while True:
      try:
        return grr_function(*args, **kwargs)
      except grr_errors.AccessForbiddenError as exception:
        print('No valid approval found: {1:s}'.format(exception)
        # If approval was already sent, just wait a bit more.
        if approval_sent:
          print('Approval not yet granted, waiting {0:d}s'.format(
              self._CHECK_APPROVAL_INTERVAL_SEC))
          time.sleep(self._CHECK_APPROVAL_INTERVAL_SEC)
          continue

        # If no approvers were specified, abort.
        if not self.approvers:
          message = ('GRR needs approval but no approvers specified '
                     '(hint: use --approvers)')
          self.state.add_error(message, critical=True)
          return None

        # Otherwise, send a request for approval
        grr_object.CreateApproval(
            reason=self.reason, notified_users=self.approvers)
        approval_sent = True
        print('{0:s}: approval request sent to: {1:s} (reason: {2:s})'.format(
            grr_object, self.approvers, self.reason))

  def cleanup(self):
    pass
