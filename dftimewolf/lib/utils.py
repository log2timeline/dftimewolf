# -*- coding: utf-8 -*-
"""Common utilities for DFTimewolf."""

from __future__ import unicode_literals

import argparse
import os
import re
import tarfile
import tempfile
from time import time

import six


TOKEN_REGEX = re.compile(r'\@([\w_]+)')


def Compress(source_path, output_directory=None):
  """Compresses files.

  Args:
    source_path (str): The data to be compressed.
    output_directory (str): The path to the output directory.

  Returns:
    str: The path to the compressed output.

  Raises:
    RuntimeError: If there are problems compressing the file.
  """
  if not output_directory:
    output_directory = tempfile.mkdtemp()

  output_file = os.path.basename(source_path)
  arcname = '{0:s}-{1:d}'.format(output_file, int(time()))
  output_file = '{0:s}.tgz'.format(arcname)
  output_file = os.path.join(output_directory, output_file)

  if os.path.exists(output_file):
    raise RuntimeError(
        'Output file {0:s} already exists.'.format(output_file))

  try:
    with tarfile.TarFile.open(output_file, 'w:gz') as tar:
      tar.add(source_path, arcname=arcname)
      tar.close()
      print(
          'The tar file has been created and can be found at: {0:s}'.format(
              output_file))
  except (IOError, tarfile.TarError) as exception:
    raise RuntimeError(
        'An error has while compressing directory {0:s}: {1!s}'.format(
            source_path, exception), critial=True)

  return output_file


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
