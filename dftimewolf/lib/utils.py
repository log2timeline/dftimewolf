# -*- coding: utf-8 -*-
"""Common utilities for DFTimewolf."""

from __future__ import unicode_literals

import re
import sys

import six

TOKEN_REGEX = re.compile(r'\@([\w_]+)')


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
    config: A dftimewolf.Config class containing configuration information

  Returns:
    The first caller of the function will receive a dictionary in which strings
    starting with "@" are replaced by the parameters in args.
  """
  if isinstance(value, six.string_types):
    for match in TOKEN_REGEX.finditer(str(value)):
      token = match.group(1)
      if token in args:
        actual_param = args[token]
        if isinstance(actual_param, six.string_types):
          value = value.replace("@"+token, args[token])
        else:
          value = actual_param
  elif isinstance(value, list):
    return [import_args_from_dict(item, args, config) for item in value]
  elif isinstance(value, dict):
    return {
        key: import_args_from_dict(val, args, config)
        for key, val in value.items()
    }
  elif isinstance(value, tuple):
    return tuple(import_args_from_dict(val, args, config) for val in value)
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
  if isinstance(value, six.string_types):
    if TOKEN_REGEX.search(value):
      raise ValueError('{0:s} must be replaced in dictionary'.format(value))
  elif isinstance(value, list):
    return [check_placeholders(item) for item in value]
  elif isinstance(value, dict):
    return {key: check_placeholders(val) for key, val in value.items()}
  elif isinstance(value, tuple):
    return tuple(check_placeholders(val) for val in value)
  return value

def signal_handler(*unused_argvs):
  """Catches Ctrl + C to exit cleanly."""
  sys.stderr.write("\nCtrl^C caught, bailing...\n")
  sys.exit(0)
