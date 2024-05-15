# -*- coding: utf-8 -*-
"""Common utilities for DFTimewolf."""

import argparse
import os
import random
import re
import string
import tarfile
import tempfile
import time
from typing import Any, Dict, Optional, Type

import pandas as pd
from dftimewolf.config import Config


TOKEN_REGEX = re.compile(r'\@([\w_]+)')


def CalculateRunTime(time_start: float) -> float:
  """Calculates a time delta used for runtime calulcations."""
  total_time = (time.time() * 1000) - (time_start * 1000)
  return round(total_time, 10)

def Compress(source_path: str, output_directory: Optional[str]=None) -> str:
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

  filename = f'{os.path.basename(source_path)}.tgz'
  filepath = os.path.join(output_directory, filename)

  while os.path.exists(filepath):
    filename = (
        f'{os.path.basename(source_path)}-'
        f'{"".join(random.sample(string.ascii_lowercase, 4))}.tgz')
    filepath = os.path.join(output_directory, filename)

  try:
    with tarfile.TarFile.open(filepath, 'w:gz') as tar:
      tar.add(source_path, arcname=filename)
      tar.close()
  except (IOError, tarfile.TarError) as exception:
    raise RuntimeError(
        'An error has while compressing directory {0:s}: {1!s}'.format(
            source_path, exception)) from exception

  return filepath


def WriteDataFrameToJsonl(df: pd.DataFrame) -> str:
  """Writes a pandas DataFrame to jsonl.

  Args:
    df: The DataFrame to output.

  Returns:
    The filename of the output file.
  """
  with tempfile.NamedTemporaryFile(
      mode='w', delete=False, encoding='utf-8', suffix='.jsonl'
      ) as output_file:
    output_file.write(
        df.to_json(orient='records', lines=True, date_format='iso'))
    return output_file.name


# preserve python2 compatibility
# pylint: disable=unnecessary-pass
class DFTimewolfFormatterClass(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter):
  """argparse formatter class. Respects whitespace and provides defaults."""
  pass


def ImportArgsFromDict(value: Any,
                       args: Dict[str, Any],
                       config: Type[Config]) -> Any:
  """Replaces some arguments by those specified by a key-value dictionary.

  This function will be recursively called on a dictionary looking for any
  value containing a "@" variable. If found, the value will be replaced
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
  if isinstance(value, str):
    for match in TOKEN_REGEX.finditer(str(value)):
      token = match.group(1)
      if token in args:
        actual_param = args[token]
        if isinstance(actual_param, str):
          value = value.replace("@"+token, actual_param)
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


# pytype: disable=bad-return-type
# mypy: disable-error-code="empty-body"
class FormatterInterface(object):
  """Interface to format text in reports."""

  # A text representation of the format.
  FORMAT = ''

  def IndentStart(self) -> str:
    """Returns formatted text for starting an indent."""
    pass

  def IndentText(self, text: str, level: int=1) -> str:
    """Return a formatted text that is indented.

    Args:
      text (str): The text to indent.
      level (int): The indentation level, may be ignored by
          some formats.

    Returns:
        str: A formatted indented string.
    """
    pass

  def IndentEnd(self) -> str:
    """Return a formatted text for ending an indent."""
    pass

  def BoldText(self, text: str) -> str:
    """Return a formatted text that will be bold."""
    pass

  def Link(self, url: str, text: str) -> str:
    """Return a formatted text that contains a link."""
    pass

  def ItalicText(self, text: str) -> str:
    """Return a formatted text that will be italic."""
    pass

  def UnderlineText(self, text: str) -> str:
    """Return a formatted text that will be underlined."""
    pass

  def Line(self) -> str:
    """Return a formatted new line."""
    pass

  def Heading(self, text: str, level: int=1) -> str:
    """Return a formatted heading."""
    pass

  def Paragraph(self, text: str) -> str:
    """Return a formatted paragraph."""
    pass
# pytype: enable=bad-return-type


class HTMLFormatter(FormatterInterface):
  """HTML formatter."""

  # A text representation of the format.
  FORMAT = 'html'

  def IndentStart(self) -> str:
    """Return formatted text for starting an indent."""
    return '<ul>'

  def IndentText(self, text: str, level: int=1) -> str:
    """Return a formatted text that is indented.

    Args:
      text (str): The text to indent.
      level (int): The indentation level, may be ignored by
          some formats.

    Returns:
        str: A formatted indented string.
    """
    return '<li>{0:s}</li>'.format(text)

  def IndentEnd(self) -> str:
    """Return a formatted text for ending an indent."""
    return '</ul>'

  def BoldText(self, text: str) -> str:
    """Return a formatted text that will be bold."""
    return '<b>{0:s}</b>'.format(text)

  def Link(self, url: str, text: str) -> str:
    """Return a formatted text that contains a link."""
    return '<a href="{0:s}" target="_blank">{1:s}</a>'.format(url, text)

  def ItalicText(self, text: str) -> str:
    """Return a formatted text that will be italic."""
    return '<i>{0:s}</i>'.format(text)

  def UnderlineText(self, text: str) -> str:
    """Return a formatted text that will be underlined."""
    return '<u>{0:s}</u>'.format(text)

  def Line(self) -> str:
    """Return a formatted new line."""
    return '<br/>'

  def Heading(self, text: str, level: int=1) -> str:
    """Return a formatted heading."""
    return '<h{0:d}>{1:s}</h{0:d}>'.format(level, text)

  def Paragraph(self, text: str) -> str:
    """Return a formatted paragraph."""
    return '<p>{0:s}</p>'.format(text)


class MarkdownFormatter(FormatterInterface):
  """Markdown formatter."""

  # A text representation of the format.
  FORMAT = 'markdown'

  def IndentText(self, text: str, level: int=1) -> str:
    """Return a formatted text that is indented.

    Args:
      text (str): The text to indent.
      level (int): The indentation level, may be ignored by
          some formats.

    Returns:
        str: A formatted indented string.
    """
    return '{0:s}+ {1:s}\n'.format(' '*(2 * level), text)

  def BoldText(self, text: str) -> str:
    """Return a formatted text that will be bold."""
    return '**{0:s}**'.format(text)

  def Link(self, url: str, text: str) -> str:
    """Return a formatted text that contains a link."""
    return '[{0:s}]({1:s})'.format(text, url)

  def ItalicText(self, text: str) -> str:
    """Return a formatted text that will be italic."""
    return '*{0:s}*'.format(text)

  def UnderlineText(self, text: str) -> str:
    """Return a formatted text that will be underlined."""
    return '**_{0:s}_**'.format(text)

  def Line(self) -> str:
    """Return a formatted new line."""
    return '\n\n'

  def Heading(self, text: str, level: int=1) -> str:
    """Return a formatted heading."""
    return '{0:s} {1:s}\n'.format('#'*level, text)

  def Paragraph(self, text: str) -> str:
    """Return a formatted paragraph."""
    return '{0:s}\n'.format(text)

  def IndentStart(self) -> str:
    """Return formatted text for starting an indent."""
    return ''

  def IndentEnd(self) -> str:
    """Return a formatted text for ending an indent."""
    return ''
