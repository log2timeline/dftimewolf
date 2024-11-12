# -*- coding: utf-8 -*-
"""Export Dataframes in the state to disk."""

from typing import Optional
import tempfile
import os
import re
import pandas as pd

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


_JSONL = 'jsonl'
_CSV = 'csv'
_MARKDOWN = 'markdown'
_MD = 'md'
_VALID_FORMATS = (_JSONL, _CSV, _MARKDOWN, _MD)

_EXTENSION_MAP = {
    _JSONL: '.jsonl',
    _CSV: '.csv',
    _MARKDOWN: '.md',
    _MD: '.md'
}


def _ConvertToValidFilename(filename: str, no_spaces: bool = True) -> str:
  """Converts a string to a valid filename.

  That is, removes special characters, and replaces them with underscores.
  Allowed characters are based on https://en.wikipedia.org/wiki/Filename,
  POSIX "Fully portable filenames".

  Args:
    filename: The filename to convert.
    no_spaces: Whether to replace spaces with underscores.

  Returns:
    A valid filename.
  """
  if no_spaces:
    filename = re.sub(r'\s', '_', filename)
  if filename[0] == '-':  # Posix filenames cannot start with a hyphen.
    filename = filename[1:]
  return re.sub(r'[^a-zA-Z0-9.]', '_', filename)


class DataFrameToDiskExporter(module.BaseModule):
  """Exports pandas Dataframes in the state to the local filesystem."""

  def __init__(
      self,
      state: DFTimewolfState,
      name: Optional[str] = None,
      critical: bool = False) -> None:
    super(DataFrameToDiskExporter, self).__init__(
        state, name=name, critical=critical)

    self._formats: list[str] = []
    self._output_dir: str = ''

  # pylint: disable=arguments-differ
  def SetUp(self, output_formats: str, output_directory: str) -> None:
    """Set up the module.

    Args:
      output_formats: Comma separated formats to export. Supported values are:
          csv, jsonl, markdown. If not specified, 'jsonl' is used.
      output_directory: Where to write the output. The directory is created if
          it doesn't already exist.
    """
    if output_formats:
      self._formats = [
        s.strip().lower() for s in output_formats.split(',') if s]
      self._formats = list(filter(None, self._formats))

      invalid_formats = []
      for f in self._formats:
        if f not in _VALID_FORMATS:
          invalid_formats.append(f)
      if invalid_formats:
        self.ModuleError(
          f'Invalid format(s) specified: {", ".join(invalid_formats)}',
          critical=True)
    else:
      self._formats = [_JSONL]

    self._output_dir = self._VerifyOrCreateOutputDirectory(output_directory)

  def Process(self) -> None:
    """Perform the exports."""
    to_export = self.state.GetContainers(containers.DataFrame)

    for df in to_export:
      self._ExportSingleContainer(df)

  def _VerifyOrCreateOutputDirectory(self, directory: str | None) -> str:
    """Checks for or creates an output directory.

    If the output directory is not specified, then a temp directory will
    be created. Otherwise, the provided value is checked for existence, and if
    it doesn't exist, is created.

    Args:
      directory: The directory path.
    """
    if not directory:
      return tempfile.mkdtemp()

    if os.path.exists(directory):
      if not os.path.isdir(directory):
        self.ModuleError(
          f'Output path {directory} already exists and is not a directory.',
          critical=True)
      return directory
    os.mkdir(directory)
    return directory

  def _ExportSingleContainer(self, container: containers.DataFrame) -> None:
    """Export a single Dataframe container.

    Args:
      container: The dataframe container to export.
    """
    for f in _VALID_FORMATS:
      if f in self._formats:
        output_path = os.path.join(
            self._output_dir,
            f'{_ConvertToValidFilename(container.name)}{_EXTENSION_MAP[f]}')

        self.logger.debug(f'Exporting {container.name} to {output_path}')

        self._ExportSingleDataframe(df=container.data_frame,
                                    output_format=f,
                                    output_path=output_path)

        self.state.StoreContainer(container=containers.File(
            name=os.path.basename(output_path),
            path=output_path,
            description=container.description))

        self.logger.debug(
            f'Export of {container.name} to {output_path} complete')

  def _ExportSingleDataframe(self,
                            df: pd.DataFrame,
                            output_format: str,
                            output_path: str) -> None:
    """Exports a single dataframe.

    Args:
      df: The dataframe to write to disk.
      output_format: The format to use.
      output_path: Where to write the output file.
    """
    with open(output_path, 'w') as f:
      if output_format == _JSONL:
        df.to_json(f, orient='records', lines=True, default_handler=str)
      elif output_format == _CSV:
        df.to_csv(f, index=False)
      elif output_format in (_MD, _MARKDOWN):
        df.to_markdown(f, index=False)


modules_manager.ModulesManager.RegisterModule(DataFrameToDiskExporter)
