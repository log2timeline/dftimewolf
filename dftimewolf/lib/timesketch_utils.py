# -*- coding: utf-8 -*-
"""Utility functions to get a Timesketch API client and an importer client."""
from __future__ import unicode_literals

import threading

from timesketch_api_client import config
from timesketch_import_client import cli


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
  """
  with LOCK:
    ts_client = state.GetFromCache('timesketch_client', default_value=None)
    if ts_client:
      return ts_client

    assistant = config.ConfigAssistant()
    assistant.load_config_file()

    # Gather all questions that are missing.
    while True:
        for field in assistant.missing:
            value = cli.ask_question(
                'What is the value for [{0:s}]'.format(field), input_type=str)
            if value:
                assistant.set_config(field, value)
        if not assistant.missing:
            break

    ts_client = assistant.get_client()
    assistant.save_config()
    state.AddToCache('timesketch_client', ts_client)
    return ts_client
