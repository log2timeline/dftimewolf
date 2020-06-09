# -*- coding: utf-8 -*-
"""Common utilities for DFTimewolf."""

import argparse
import re

import six


TOKEN_REGEX = re.compile(r'\@([\w_]+)')


# preserve python2 compatibility
# pylint: disable=unnecessary-pass
class DFTimewolfFormatterClass(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter):
  """argparse formatter class. Respects whitespace and provides defaults."""
  pass


def ImportArgsFromDict(value, args, config):
  """Replaces some arguments by those specified by a key-value dictionary.

  This function will be recursively called on a dictionary looking for any
  value containing a "$" variable. If found, the value will be replaced
  by the attribute in "args" of the same name.

  It is used to load arguments from the CLI and any extra configuration
  parameters passed in recipes.

  Args:
    value (object): The value a dictionary. This is passed recursively and may
        change in nature: string, list, or dict. The top-level variable should
        be the dictionary that is supposed to be recursively traversed.
    args (dict[str, object]): dictionary used to do replacements.
    config (dftimewolf.Config): class containing configuration information

  Returns:
    object: the first caller of the function will receive a dictionary in
        which strings starting with "@" are replaced by the parameters in args.
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
    return [ImportArgsFromDict(item, args, config) for item in value]
  elif isinstance(value, dict):
    return {
        key: ImportArgsFromDict(val, args, config)
        for key, val in value.items()
    }
  elif isinstance(value, tuple):
    return tuple(ImportArgsFromDict(val, args, config) for val in value)
  return value
