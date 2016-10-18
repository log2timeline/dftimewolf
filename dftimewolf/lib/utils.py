#!/usr/bin/env python
"""Common utilities for Timewolf."""

import getpass
import netrc
import os
import sys

import pytz


class TimewolfConsoleOutput(object):
  """Send messages to stdin or stderr."""

  def __init__(self, sender, verbose):
    """Initializer the Timewolf console output object."""
    super(TimewolfConsoleOutput, self).__init__()
    self._sender = sender
    self._verbose = verbose

  def _FormatMessage(self, message):
    """Format message with script name and sender name.

    Args:
      message: Message to be formatted
    Returns:
      String containing formatted message
    """
    script_name = os.path.basename(sys.argv[0])
    formatted_message = u'{0:s}: {1:s} - {2:s}\n'.format(script_name,
                                                         self._sender, message)
    return formatted_message

  def StdOut(self, message):
    """Send message to standard out.

    Args:
      message: Message to be printed
    """
    sys.stdout.write(u'{0:s}\n'.format(message))
    sys.stdout.flush()

  def StdErr(self, message, die=False):
    """Send formatted message to standard error.

    Args:
      message: Message to be printed
      die: Boolean indicating whether error is irrecoverable
    """
    error_message = self._FormatMessage(message)
    if die:
      exit_message = error_message.rstrip(u'\n')
      sys.exit(exit_message)
    sys.stderr.write(error_message)
    sys.stderr.flush()

  def VerboseOut(self, message):
    """Send verbose output to standard error.

    Args:
      message: Message to be printed
    """
    if self._verbose:
      self.StdErr(message, die=False)


def ReadFromStdin():
  """Convenience function to read input from stdin."""
  for line in sys.stdin:
    path_name = line.strip(u'\n').split()
    try:
      path = path_name[0]
      name = path_name[1]
    except IndexError:
      raise IndexError(u'Malformed input on stdin')
  yield (path, name)


def IsValidTimezone(timezone):
  """Check timezone string against known timezones in the pytz package.

  Args:
    timezone: Timezone name
  """
  return timezone in pytz.all_timezones


def GetCredentials(user, host):
  """Attempts to return credentials from netrc file, prompting otherwise."""
  netrc_file = netrc.netrc()
  netrc_entry = netrc_file.authenticators(host)
  if netrc_entry:
    username = netrc_entry[0]
    password = netrc_entry[2]
  else:
    username = user
    password = getpass.getpass()

  return username, password
