"""Authentication module."""
import os.path
from typing import Optional

import filelock
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


def GetGoogleOauth2Credential(
    scopes: list[str], credential_path: str, secret_path: str
) -> Optional[Credentials]:
  """Gets a Google Oauth2 credential.
  
  Args:
    scopes (list[str]): List of scopes to request.
    credential_path (str): Path to the credentials file.
    secret_path (str): Path to the secret file.
  
  Returns:
    Optional[Credentials]: Google Oauth2 credential.
  """
  credentials: Optional[Credentials] = None

  # The credentials file stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  credentials_path = os.path.join(os.path.expanduser("~"), credential_path)
  lock = filelock.FileLock(credentials_path + ".lock")  # pylint: disable=abstract-class-instantiated
  with lock:
    if os.path.exists(credentials_path):
      credentials = Credentials.from_authorized_user_file(
          credentials_path, scopes
      )

    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
      if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
      else:
        secrets_path = os.path.join(os.path.expanduser("~"), secret_path)
        if not os.path.exists(secrets_path):
          error_message = (
              "No OAuth application credentials available to retrieve "
              "workspace logs. Please generate OAuth application credentials "
              "(see https://developers.google.com/workspace/guides/"
              "create-credentials#desktop) and save them to {0:s}."
          ).format(secrets_path)
          raise RuntimeError(error_message)
        flow = InstalledAppFlow.from_client_secrets_file(secrets_path, scopes)
        credentials = flow.run_local_server()

      # Save the credentials for the next run
      if credentials:
        with open(credentials_path, "w") as token_file:
          token_file.write(credentials.to_json())

  return credentials
