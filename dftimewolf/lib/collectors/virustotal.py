# -*- coding: utf-8 -*-
"""Downloads several items for a VT file."""

import os
import tempfile
import urllib.parse
import zipfile
from io import BufferedWriter
from typing import List, Optional, Union

import vt

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class VTCollector(module.BaseModule):
  """VirusTotal (VT) Collector.

  Attributes:
    hashes_list: List of hashes passed ot the module
    vt_type: pcap or evtx depending on the file type requested

  """

  def __init__(
      self,
      state: DFTimewolfState,
      name: Optional[str],
      critical: bool = False) -> None:
    """Initializes an VirusTotal (VT) collector.

    Args:
      state: recipe state.
      name: The module's runtime name.
      critical: True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(VTCollector, self).__init__(state, name=name, critical=critical)
    self.hashes_list: List[str] = []
    self.directory = ''
    self.client = None  # type: vt.Client
    self.vt_type = ''

  def Process(self) -> None:
    """Process of the VirusTotal collector after setup"""

    for vt_hash in self.hashes_list:
      try:
        download_link_list = self._getDownloadLinks(vt_hash)
      except vt.error.APIError:
        self.logger.info(f'Hash not found on VT: {vt_hash}')

      for download_link in download_link_list:
        filename = f'{vt_hash}.{self.vt_type}'

        file = self._downloadFile(download_link, filename)

        if file is None:
          self.logger.warning(
              f'File not found {urllib.parse.quote(download_link)}')
          continue

        self._createContainer(vt_hash=vt_hash, file=file)

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(
      self,
      hashes: str,
      vt_api_key: str,
      vt_type: str,
      directory: str,
  ) -> None:
    """Sets up an VirusTotal (VT) collector.

    Args:
      hashes: Coma seperated strings of hashes
      vt_api_key: VirusTotal Enterprise API Key
      vt_type: Which file to fetch
      directory: Where to store the downloaded files to
    """

    self.directory = self._CheckOutputPath(directory)

    if not hashes:
      self.ModuleError('You need to specify at least one hash', critical=True)

    if not vt_type:
      self.ModuleError(
          "You need to specify a vt_type from: pcap, evtx", critical=True)

    assert vt_type is not None

    self.vt_type = vt_type

    self.hashes_list = [item.strip() for item in hashes.strip().split(',')]

    if not vt_api_key:
      self.ModuleError(
          'You need to specify a VirusTotal Enterprise API key',
          critical=True,
      )

    self.client = vt.Client(vt_api_key)

    if self.client is None:
      self.ModuleError(
          'Error creating VirusTotal Client instance',
          critical=True,
      )

  def _downloadFile(self, download_link: str,
                    filename: str) -> Union[BufferedWriter, None]:
    """Downloads a file to a given filename.

    Args:
      download_link: URL to be downloaded.
      filename: Filename the output will be written to.

    Returns:
      BufferedWriter of the written file
      None: if nothing is found
    """
    self.logger.info(f'Download link {urllib.parse.quote(download_link)}')

    download = self.client.get(download_link)
    if download.status == 200:
      file_content = download.content.read()

      if len(file_content) == 0:
        return None
      download_file_path = os.path.join(self.directory, filename)
      self.logger.info(
          f'Downloaded file will be written to: {download_file_path}')
      file = open(download_file_path, "wb")
      file.write(file_content)
      file.close()

    assert isinstance(file, BufferedWriter)

    return file

  def _createContainer(self, vt_hash: str, file: BufferedWriter) -> None:
    """Creates the container for the next steps.

    Args:
      vt_hash: Hash of the sample.
      file: BufferedWriter of the written file that will be in the container.
    """

    if self.vt_type == 'pcap':
      file_container = containers.File(name=vt_hash, path=file.name)
      self.StoreContainer(file_container)

    if self.vt_type == 'evtx':
      # Unzip the file so that plaso can go over EVTX part in the archive
      extract_output_dir = f'{file.name}_extract'
      if not os.path.isdir(extract_output_dir):
        os.makedirs(extract_output_dir)

      with zipfile.ZipFile(file.name) as archive:
        archive.extractall(path=extract_output_dir)
        self.logger.debug(f'{file.name} file extracted to {extract_output_dir}')

      dir_container = containers.Directory(
          name=vt_hash, path=os.path.abspath(extract_output_dir))
      self.StoreContainer(dir_container)

  def _CheckOutputPath(self, directory: str) -> str:
    """Checks that the output path can be manipulated by the module.

    Args:
      directory: Full path to the output directory where files will be
          dumped.

    Returns:
      The full path to the directory where files will be dumped.
    """
    # Check that the output path can be manipulated
    if not directory:
      return tempfile.mkdtemp()
    if os.path.exists(directory):
      return directory

    try:
      os.makedirs(directory)
      return directory
    except OSError as error:
      self.ModuleError(
          f'{directory} error while creating the output directory: {error}',
          critical=True,
      )
      return tempfile.mkdtemp()

  def _getDownloadLinks(self, vt_hash: str) -> List[str]:
    """Checks if a hash has a Pcap or Evtx file available.
    Returns a list of the URLs for download.
    One hash can have multiple Pcaps / Evtx available.

    Args:
      vt_hash: A hash.

    Returns:
      list: List of strings with URLs to the requested files.
    """
    assert self.client is not None

    vt_data = self.client.get_data(f'/files/{vt_hash}/behaviours')
    return_list = []

    for analysis in vt_data:
      if analysis['attributes'][f'has_{self.vt_type}']:
        analysis_link = f'{analysis["links"]["self"]}/{self.vt_type}'
        self.logger.info(
            f'{self.vt_type} for {vt_hash}: {urllib.parse.quote(analysis_link)}'
        )
        return_list.append(analysis_link)

    return return_list


modules_manager.ModulesManager.RegisterModule(VTCollector)
