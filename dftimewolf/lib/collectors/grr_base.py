"""Base GRR module class. GRR modules should extend it."""

import tempfile
import time
from logging import Logger
from typing import Any, Callable, Optional, Union

from grr_api_client import api as grr_api
from grr_api_client import errors as grr_errors
from grr_api_client.client import Client
from grr_api_client.flow import Flow
from grr_api_client.hunt import Hunt

from dftimewolf.lib.errors import DFTimewolfError


class GRRBaseModule:
  """Base module for GRR hunt and flow modules.

  Attributes:
    output_path (str): path to store collected artifacts.
    grr_api: GRR HTTP API client.
    grr_url: GRR HTTP URL.
    reason (str): justification for GRR access.
    approvers: list of GRR approval recipients.
    message_callback: Callback method used to notify the operator of approval
        URLs.
  """

  _CHECK_APPROVAL_INTERVAL_SEC = 10

  def __init__(self) -> None:
    """Initializes a GRR hunt or flow module.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional[str]): The module's runtime name.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    self.reason = str()
    self.grr_api: grr_api.GrrApi = None
    self.grr_url = str()
    self.approvers = []  # type: list[str]
    self.output_path = str()
    self.message_callback: Callable[[str, bool], None] = None  # type: ignore

  # pylint: disable=arguments-differ
  def GrrSetUp(
      self,
      reason: str,
      grr_server_url: str,
      grr_username: str,
      grr_password: str,
      message_callback: Callable[[str, bool], None],
      approvers: Optional[str]=None,
      verify: bool=True) -> None:
    """Initializes a GRR hunt result collector.

    Args:
      reason (str): justification for GRR access.
      grr_server_url (str): GRR server URL.
      grr_username (str): GRR username.
      grr_password (str): GRR password.
      message_callback: Callback method used to notify the operator of approval
          URLs.
      approvers (Optional[str]): comma-separated GRR approval recipients.
      verify (Optional[bool]): True to indicate GRR server's x509 certificate
          should be verified.
    """
    grr_auth = (grr_username, grr_password)
    if approvers:
      self.approvers = [item.strip() for item in approvers.split(',')]
    self.grr_api = grr_api.InitHttp(api_endpoint=grr_server_url,
                                    auth=grr_auth,
                                    verify=verify)
    self.grr_url = grr_server_url
    self.output_path = tempfile.mkdtemp()
    self.reason = reason
    self.message_callback = message_callback

  # TODO: change object to more specific GRR type information.
  def _WrapGRRRequestWithApproval(
    self,
    grr_object: Union[Hunt, Client],
    grr_function: Callable,  # type: ignore[type-arg]
    logger: Logger,
    telemetry_callback: Callable[[dict[str, str]], None],
    *args: Any,
    **kwargs: Any,
  ) -> Union[Flow, Hunt]:
    """Wraps a GRR request with approval.

    This method will request the approval if not yet granted.

    Args:
      grr_object (object): GRR object to create the eventual approval on.
      grr_function (function): GRR function requiring approval.
      logger (Logger): logging object coming from the module.
      telemetry_callback (Callback[dict[str, str]]): telemetry callback.
          Necessary since this is not a Module but a regular object.
      args (list[object]): Positional arguments that are to be passed
          to `grr_function`.
      kwargs (dict[str, object]): keyword arguments that are to be passed
          to `grr_function`.

    Returns:
      object: return value of the execution of grr_function(*args, **kwargs).
    Raises:
      DFTimewolfError: If approvers are required but none were specified.
    """
    approval_sent = False
    approval_url = None
    approval_url_shown = False
    start = time.time()
    telemetry_callback({"mpa_start": str(start)})
    while True:
      try:
        result = grr_function(*args, **kwargs)
        telemetry_callback({"mpa_success": str(time.time())})
        telemetry_callback({"mpa_duration": str(time.time() - start)})
        return result
      except grr_errors.AccessForbiddenError as exception:
        logger.warning(f"No valid approval found: {exception!s}")
        # If approval was already sent, just wait a bit more.
        if approval_sent:
          logger.info(
            "Approval not yet granted, waiting {0:d}s".format(
              self._CHECK_APPROVAL_INTERVAL_SEC
            )
          )
          if not approval_url_shown:
            self.message_callback(f"Approval needed at: {approval_url}", False)
            approval_url_shown = True
          else:
            logger.info(f"Approval needed at: {approval_url}")
          time.sleep(self._CHECK_APPROVAL_INTERVAL_SEC)
          continue

        # If no approvers were specified, abort.
        if not self.approvers:
          message = (
            "GRR needs approval but no approvers specified "
            "(hint: use --approvers)"
          )
          raise DFTimewolfError(message, critical=True) from exception

        # Otherwise, send a request for approval
        approval = grr_object.CreateApproval(
          reason=self.reason, notified_users=self.approvers
        )
        approval_sent = True
        if hasattr(approval, "client_id"):
          approval_url = (
            f"{self.grr_url}/v2/clients/{approval.client_id}"
            f"/approvals/{approval.approval_id}/users/{approval.username}"
          )
        elif hasattr(approval, "hunt_id"):
          approval_url = (
            f"{self.grr_url}/v2/hunts/{approval.hunt_id}"
            f"/approvals/{approval.approval_id}/users/{approval.username}"
          )
        logger.info(
          f"{grr_object}: approval request sent to: "
          f"{self.approvers} (reason: {self.reason})"
        )
