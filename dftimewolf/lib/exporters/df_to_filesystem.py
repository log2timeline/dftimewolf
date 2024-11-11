# -*- coding: utf-8 -*-
"""Export Dataframes in the state to disk."""

from typing import Optional
import tempfile
import os
import re

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


_JSONL = 'jsonl'
_CSV = 'csv'
_MARKDOWN = 'markdown'
_VALID_OUTPUTS = (_JSONL, _CSV, _MARKDOWN)


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
        if f not in _VALID_OUTPUTS:
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
      self._ExportSingleDataFrame(df)

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

  def _ExportSingleDataFrame(self, container: containers.DataFrame) -> None:
    """Export a single Dataframe container.

    Args:
      df_cont: The dataframe container to export.
    """
    if _JSONL in self._formats:
      self._ExportDataFrameJSONL(container)
    if _CSV in self._formats:
      self._ExportDataFrameCSV(container)
    if _MARKDOWN in self._formats:
      self._ExportDataFrameMarkdown(container)

  def _ExportDataFrameJSONL(self, container: containers.DataFrame) -> None:
    """Exports a single dataframe container to a jsonl file."""
    output_path = os.path.join(
      self._output_dir, f'{_ConvertToValidFilename(container.name)}.{_JSONL}')
    self.logger.debug(f'Exporting {container.name} to {output_path}')

    with open(output_path, 'w') as f:
      container.data_frame.to_json(
        f, orient='records', lines=True, default_handler=str)

    self.state.StoreContainer(container=containers.File(
        name=os.path.basename(output_path),
        path=output_path,
        description=container.description))

    self.logger.debug(f'Export of {container.name} to {output_path} complete')

  def _ExportDataFrameCSV(self, container: containers.DataFrame) -> None:
    """Exports a single dataframe container to a csv file."""
    output_path = os.path.join(
      self._output_dir, f'{_ConvertToValidFilename(container.name)}.{_CSV}')
    self.logger.debug(f'Exporting {container.name} to {output_path}')

    with open(output_path, 'w') as f:
      container.data_frame.to_csv(f, index=False)

    self.state.StoreContainer(container=containers.File(
        name=os.path.basename(output_path),
        path=output_path,
        description=container.description))

    self.logger.debug(f'Export of {container.name} to {output_path} complete')

  def _ExportDataFrameMarkdown(self, container: containers.DataFrame) -> None:
    """Exports a single dataframe container to a markdown file."""
    output_path = os.path.join(
      self._output_dir, f'{_ConvertToValidFilename(container.name)}.md')
    self.logger.debug(f'Exporting {container.name} to {output_path}')

    with open(output_path, 'w') as f:
      container.data_frame.to_markdown(f, index=False)

    self.state.StoreContainer(container=containers.File(
        name=os.path.basename(output_path),
        path=output_path,
        description=container.description))

    self.logger.debug(f'Export of {container.name} to {output_path} complete')


modules_manager.ModulesManager.RegisterModule(DataFrameToDiskExporter)
