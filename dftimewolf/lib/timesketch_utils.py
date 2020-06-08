# -*- coding: utf-8 -*-
"""Utility functions to get a Timesketch API client and an importer client."""
import threading

from timesketch_api_client import config
from timesketch_api_client import crypto


LOCK = threading.Lock()


def GetApiClient(state):
  """Returns a Timesketch API client using thread safe methods.

  This function either returns an API client that has been stored
  in the state object, or if not it will read Timesketch RC files
  to configure a Timesketch API client. If the RC file does not exist
  or is missing values questions will be asked to fully configure
  the client.

  Args:
    state (DFTimewolfState): recipe state.

  Returns:
    object: A timesketch API object (instance of TimesketchApi).
  """
  with LOCK:
    ts_client = state.GetFromCache('timesketch_client', default_value=None)
    if ts_client:
      return ts_client

    assistant = config.ConfigAssistant()
    assistant.load_config_file()

    # TODO: support user supplied passwords to decrypt token file.
    config.configure_missing_parameters(config_assistant=assistant)
    ts_client = assistant.get_client()
    assistant.save_config()

    cred_storage = crypto.CredentialStorage()
    cred_storage.save_credentials(
        ts_client.credentials, config_assistant=assistant)

    state.AddToCache('timesketch_client', ts_client)
    return ts_client
