# -*- coding: utf-8 -*-
"""Common utilities for DFTimewolf."""

from __future__ import unicode_literals

from datetime import datetime
import os
import re
import sys

import pytz

TOKEN_REGEX = re.compile(r'\@(\w+)')


class DFTimewolfConsoleOutput(object):
  """Send messages to stdin or stderr."""

  def __init__(self, sender, verbose):
    """Initialize the DFTimewolf console output object.

    Args:
      sender: Name of the sender of the message
      verbose: Boolean indicating if verbose output is to be used
    """
    super(DFTimewolfConsoleOutput, self).__init__()
    self._sender = sender
    self._verbose = verbose

  def _FormatMessage(self, message):
    """Format message with timestamp, script name and sender name.

    Args:
      message: Message to be formatted
    Returns:
      String containing formatted message
    """
    script_name = os.path.basename(sys.argv[0])
    timestamp = datetime.now().isoformat()
    formatted_message = '[{0:s}] {1:s}: {2:s} - {3:s}\n'.format(
        timestamp, script_name, self._sender, message)
    return formatted_message

  def StdOut(self, message):
    """Send message to standard out.

    Args:
      message: Message to be printed
    """
    sys.stdout.write('{0:s}\n'.format(message))
    sys.stdout.flush()

  def StdErr(self, message, die=False):
    """Send formatted message to standard error.

    Args:
      message: Message to be printed
      die: Boolean indicating whether error is irrecoverable
    """
    error_message = self._FormatMessage(message)
    if die:
      exit_message = error_message.rstrip('\n')
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
  """Convenience function to read input from stdin.

  Yields:
    Tuple of path to artifacts or processed artifacts and a name
  """
  for line in sys.stdin:
    path_name = line.strip('\n').split()
    try:
      path = path_name[0]
      name = path_name[1]
    except IndexError:
      raise IndexError('Malformed input on stdin')
    yield (path, name)


def IsValidTimezone(timezone):
  """Check timezone string against known timezones in the pytz package.

  Args:
    timezone: Timezone name
  Returns:
    Boolean indicating if the timezone name is known to the pytz package
  """
  return timezone in pytz.all_timezones


def import_args_from_dict(value, args, config):
  """Replaces some arguments by those specified by a key-value dictionary.

  This function will be recursively called on a dictionary looking for any
  value containing a "$" variable. If found, the value will be replaced
  by the attribute in "args" of the same name.

  It is used to load arguments from the CLI and any extra configuration
  parameters passed in recipes.

  Args:
    value: The value of a {key: value} dictionary. This is passed recursively
        and may change in nature: string, list, or dict. The top-level variable
        should be the dictionary that is supposed to be recursively traversed.
    args: A {key: value} dictionary used to do replacements.

  Returns:
    The first caller of the function will receive a dictionary in which strings
    starting with "@" are replaced by the parameters in args.
  """

  if isinstance(value, (str, unicode)):
    match = TOKEN_REGEX.search(str(value))
    if match and args.get(match.group(1)):
      return TOKEN_REGEX.sub(args[match.group(1)] or '', value)
    if match and config.get_extra(str(match.group(1))):
      return TOKEN_REGEX.sub(config.get_extra(str(match.group(1))) or '', value)
  elif isinstance(value, list):
    return [import_args_from_dict(item, args, config) for item in value]
  elif isinstance(value, dict):
    return {
        key: import_args_from_dict(val, args, config)
        for key, val in value.items()
    }
  return value


def check_placeholders(value):
  """Checks if any values in a given dictionary still contain @ parameters.

  Args:
    value: Dictionary, list, or string that will be recursively checked for
        placeholders

  Raises:
    ValueError: There still exists a value with an @ parameter.

  Returns:
    Top-level caller: a modified dict with replaced tokens.
    Recursive caller: a modified object with replaced tokens.
  """
  if isinstance(value, (str, unicode)):
    if TOKEN_REGEX.search(value):
      raise ValueError('{0:s} must be replaced in dictionary'.format(value))
  elif isinstance(value, list):
    return [check_placeholders(item) for item in value]
  elif isinstance(value, dict):
    return {key: check_placeholders(val) for key, val in value.items()}
  return value
