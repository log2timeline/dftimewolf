#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the auth library."""

import unittest
from unittest import mock
import os

from dftimewolf.lib import auth
from google.oauth2.credentials import Credentials


class AuthTest(unittest.TestCase):
  """Tests for the auth library."""

  def setUp(self):
    self.scopes = ["scope1"]
    self.credential_path = "creds.json"
    self.secret_path = "secret.json"

  @mock.patch("dftimewolf.lib.auth.os.path.expanduser")
  @mock.patch("dftimewolf.lib.auth.os.path.exists")
  @mock.patch("dftimewolf.lib.auth.Credentials")
  @mock.patch("dftimewolf.lib.auth.filelock.FileLock")
  def testGetGoogleOauth2CredentialValid(
      self, mock_filelock, mock_credentials, mock_exists, mock_expanduser
  ):
    """Tests getting valid credentials from file."""
    mock_expanduser.return_value = "/tmp"
    mock_exists.return_value = True

    mock_creds = mock.Mock()
    mock_creds.valid = True
    mock_credentials.from_authorized_user_file.return_value = mock_creds

    creds = auth.GetGoogleOauth2Credential(
        self.scopes, self.credential_path, self.secret_path
    )

    self.assertEqual(creds, mock_creds)
    mock_credentials.from_authorized_user_file.assert_called_once()

  @mock.patch("dftimewolf.lib.auth.os.path.expanduser")
  @mock.patch("dftimewolf.lib.auth.os.path.exists")
  @mock.patch("dftimewolf.lib.auth.Credentials")
  @mock.patch("dftimewolf.lib.auth.filelock.FileLock")
  @mock.patch("dftimewolf.lib.auth.Request")
  @mock.patch("builtins.open", new_callable=mock.mock_open)
  def testGetGoogleOauth2CredentialExpiredRefreshable(
      self,
      mock_open,
      mock_request,
      mock_filelock,
      mock_credentials,
      mock_exists,
      mock_expanduser,
  ):
    """Tests refreshing expired credentials."""
    mock_expanduser.return_value = "/tmp"
    mock_exists.return_value = True

    mock_creds = mock.Mock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "token"
    mock_credentials.from_authorized_user_file.return_value = mock_creds

    creds = auth.GetGoogleOauth2Credential(
        self.scopes, self.credential_path, self.secret_path
    )

    mock_creds.refresh.assert_called_once()
    mock_open.assert_called_once()  # Should save refreshed creds

  @mock.patch("dftimewolf.lib.auth.os.path.expanduser")
  @mock.patch("dftimewolf.lib.auth.os.path.exists")
  @mock.patch("dftimewolf.lib.auth.InstalledAppFlow")
  @mock.patch("dftimewolf.lib.auth.filelock.FileLock")
  @mock.patch("builtins.open", new_callable=mock.mock_open)
  def testGetGoogleOauth2CredentialNoCredsSecretExists(
      self, mock_open, mock_filelock, mock_flow, mock_exists, mock_expanduser
  ):
    """Tests full flow when no credentials exist but secret does."""
    mock_expanduser.return_value = "/tmp"
    # First check for creds (False), then for secret (True)
    mock_exists.side_effect = [False, True]

    mock_flow_instance = mock.Mock()
    mock_flow.from_client_secrets_file.return_value = mock_flow_instance
    mock_creds = mock.Mock()
    mock_flow_instance.run_local_server.return_value = mock_creds

    creds = auth.GetGoogleOauth2Credential(
        self.scopes, self.credential_path, self.secret_path
    )

    self.assertEqual(creds, mock_creds)
    mock_flow.from_client_secrets_file.assert_called_once()
    mock_flow_instance.run_local_server.assert_called_once()
    mock_open.assert_called_once()

  @mock.patch("dftimewolf.lib.auth.os.path.expanduser")
  @mock.patch("dftimewolf.lib.auth.os.path.exists")
  @mock.patch(
      "dftimewolf.lib.auth.InstalledAppFlow"
  )  # Mock this to avoid actual run_local_server call if logic fails
  @mock.patch("dftimewolf.lib.auth.filelock.FileLock")
  def testGetGoogleOauth2CredentialNoCredsNoSecret(
      self, mock_filelock, mock_flow, mock_exists, mock_expanduser
  ):
    """Tests error when neither credentials nor secret exist."""
    mock_expanduser.return_value = "/tmp"
    # First check for creds (False), then for secret (False)
    mock_exists.side_effect = [False, False]

    with self.assertRaises(RuntimeError):
      auth.GetGoogleOauth2Credential(
          self.scopes, self.credential_path, self.secret_path
      )

  @mock.patch("dftimewolf.lib.auth.os.path.expanduser")
  @mock.patch("dftimewolf.lib.auth.os.path.exists")
  @mock.patch("dftimewolf.lib.auth.InstalledAppFlow")
  @mock.patch("dftimewolf.lib.auth.Credentials")
  @mock.patch("dftimewolf.lib.auth.filelock.FileLock")
  @mock.patch("builtins.open", new_callable=mock.mock_open)
  def testGetGoogleOauth2CredentialInvalidNotRefreshable(
      self,
      mock_open,
      mock_filelock,
      mock_credentials,
      mock_flow,
      mock_exists,
      mock_expanduser,
  ):
    """Tests flow when credentials are invalid and not refreshable."""
    mock_expanduser.return_value = "/tmp"
    # Creds exist, Secret exists
    mock_exists.side_effect = [True, True]

    mock_creds = mock.Mock()
    mock_creds.valid = False
    mock_creds.expired = (
        False  # Not expired, just invalid? Or expired but no refresh token
    )
    mock_creds.refresh_token = None
    mock_credentials.from_authorized_user_file.return_value = mock_creds

    mock_flow_instance = mock.Mock()
    mock_flow.from_client_secrets_file.return_value = mock_flow_instance
    mock_new_creds = mock.Mock()
    mock_flow_instance.run_local_server.return_value = mock_new_creds

    creds = auth.GetGoogleOauth2Credential(
        self.scopes, self.credential_path, self.secret_path
    )

    self.assertEqual(creds, mock_new_creds)
    mock_flow.from_client_secrets_file.assert_called_once()
    mock_open.assert_called_once()


if __name__ == "__main__":
  unittest.main()
