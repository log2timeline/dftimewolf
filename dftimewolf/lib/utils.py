# -*- coding: utf-8 -*-
"""Common utilities for DFTimewolf."""

import argparse
import os
import re
import tarfile
import tempfile
from time import time
from typing import Any, Dict, Optional, Type

from dftimewolf.config import Config

TOKEN_REGEX = re.compile(r'\@([\w_]+)')


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

  output_file = os.path.basename(source_path)
  arcname = f'{time()}-{output_file}'
  output_file = f'{arcname}.tgz'
  output_file = os.path.join(output_directory, output_file)

  if os.path.exists(output_file):
    raise RuntimeError(f'Output file {output_file} already exists.')

  try:
    with tarfile.TarFile.open(output_file, 'w:gz') as tar:
      tar.add(source_path, arcname=arcname)
      tar.close()
  except (IOError, tarfile.TarError) as exception:
    raise RuntimeError(
        f'An error has while compressing directory {source_path}: {exception}'
        ) from exception

  return output_file


# preserve python2 compatibility
# pylint: disable=unnecessary-pass
class DFTimewolfFormatterClass(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter):
  """argparse formatter class. Respects whitespace and provides defaults."""
  pass


def ImportArgsFromDict(value: Any,
                       args: Dict[str,
                       Any],
                       config: Type[Config]) -> Any:
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


class FormatterInterface(object):
  """Interface to format text in reports."""

  # A text representation of the format.
  FORMAT = ''

  def IndentStart(self) -> str:
    """Return formatted text for starting an indent."""
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
    return f'<li>{text}</li>'

  def IndentEnd(self) -> str:
    """Return a formatted text for ending an indent."""
    return '</ul>'

  def BoldText(self, text: str) -> str:
    """Return a formatted text that will be bold."""
    return f'<b>{text}</b>'

  def Link(self, url: str, text: str) -> str:
    """Return a formatted text that contains a link."""
    return f'<a href="{url}" target="_blank">{text}</a>'

  def ItalicText(self, text: str) -> str:
    """Return a formatted text that will be italic."""
    return f'<i>{text}</i>'

  def UnderlineText(self, text: str) -> str:
    """Return a formatted text that will be underlined."""
    return f'<u>{text}</u>'

  def Line(self) -> str:
    """Return a formatted new line."""
    return '<br/>'

  def Heading(self, text: str, level: int=1) -> str:
    """Return a formatted heading."""
    return f'<h{level}>{text}</h{level}>'

  def Paragraph(self, text: str) -> str:
    """Return a formatted paragraph."""
    return f'<p>{text}</p>'


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
    return f"{' '*(2 * level)}+ {text}\n"

  def BoldText(self, text: str) -> str:
    """Return a formatted text that will be bold."""
    return f'**{text}**'

  def Link(self, url: str, text: str) -> str:
    """Return a formatted text that contains a link."""
    return f'[{text}]({url})'

  def ItalicText(self, text: str) -> str:
    """Return a formatted text that will be italic."""
    return f'*{text}*'

  def UnderlineText(self, text: str) -> str:
    """Return a formatted text that will be underlined."""
    return f'**_{text}_**'

  def Line(self) -> str:
    """Return a formatted new line."""
    return '\n\n'

  def Heading(self, text: str, level: int=1) -> str:
    """Return a formatted heading."""
    return f"{'#'*level} {text}\n"

  def Paragraph(self, text: str) -> str:
    """Return a formatted paragraph."""
    return f'{text}\n'

  def IndentStart(self) -> str:
    """Return formatted text for starting an indent."""
    return ''

  def IndentEnd(self) -> str:
    """Return a formatted text for ending an indent."""
    return ''
