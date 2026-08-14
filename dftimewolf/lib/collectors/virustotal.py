# -*- coding: utf-8 -*-
"""Downloads several items for a VT file."""

import os
import tempfile
import urllib.parse
import zipfile
from typing import Callable

import vt

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib import cache
from dftimewolf.lib import spanner_telemetry as telemetry
from dftimewolf.lib.containers import manager as container_manager


class VTCollector(module.BaseModule):
  """VirusTotal (VT) Collector.

  Attributes:
    hashes_list: List of hashes passed ot the module
    vt_type: pcap or evtx depending on the file type requested

  """

  def __init__(self,
               name: str,
               container_manager_: container_manager.ContainerManager,
               cache_: cache.DFTWCache,
               telemetry_: telemetry.BaseTelemetry,
               publish_message_callback: Callable[[str, str, bool], None]):
    """Initializes an VirusTotal (VT) collector.

    Args:
      name: The modules runtime name.
      container_manager_: A common container manager object.
      cache_: A common DFTWCache object.
      telemetry_: A common telemetry collector object.
      publish_message_callback: A callback to send modules messages to.
    """
    super().__init__(name=name,
                     cache_=cache_,
                     container_manager_=container_manager_,
                     telemetry_=telemetry_,
                     publish_message_callback=publish_message_callback)

    self.hashes_list: list[str] = []
    self.directory = ''
    self.client: vt.client.Client
    self.vt_type = ''

  def Process(self) -> None:
    """Process of the VirusTotal collector after setup"""

    for vt_hash in self.hashes_list:
      try:
        download_link_list = self._getDownloadLinks(vt_hash)

        for download_link in download_link_list:
          filename = f'{vt_hash}.{self.vt_type}'

          downloaded_filepath = self._downloadFile(download_link, filename)

          if downloaded_filepath is None:
            self.logger.warning(
                f'File not found {urllib.parse.quote(download_link)}')
            continue

          self._createContainer(vt_hash=vt_hash, filepath=downloaded_filepath)
      except vt.error.APIError:
        self.logger.warning(f"Hash not found on VT: {vt_hash}")

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

  def _downloadFile(self,
                    download_link: str,
                    filename: str) -> str | None:
    """Downloads a file to a given filename.

    Args:
      download_link: URL to be downloaded.
      filename: Filename the output will be written to.

    Returns:
      BufferedWriter of the written file
      None: if nothing is found
    """
    self.logger.debug(f"Download link {urllib.parse.quote(download_link)}")

    download = self.client.get(download_link)
    if download.status != 200:
      return None

    file_content = download.content.read()

    if len(file_content) == 0:
      return None
    download_file_path = os.path.join(self.directory, filename)
    file = open(download_file_path, "wb")
    file.write(file_content)
    file.close()
    self.logger.info(f"File downloaded to: {download_file_path}")

    return download_file_path

  def _createContainer(self, vt_hash: str, filepath: str) -> None:
    """Creates the container for the next steps.

    Args:
      vt_hash: Hash of the sample.
      file: BufferedWriter of the written file that will be in the container.
    """

    if self.vt_type == 'pcap':
      file_container = containers.File(name=vt_hash, path=filepath)
      self.StoreContainer(file_container)

    if self.vt_type == 'evtx':
      # Unzip the file so that plaso can go over EVTX part in the archive
      extract_output_dir = f'{filepath}_extract'
      if not os.path.isdir(extract_output_dir):
        os.makedirs(extract_output_dir)

      with zipfile.ZipFile(filepath) as archive:
        archive.extractall(path=extract_output_dir)
        self.logger.debug(f'{filepath} file extracted to {extract_output_dir}')

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

  def _getDownloadLinks(self, vt_hash: str) -> list[str]:
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
        self.logger.debug(
          f"{self.vt_type} for {vt_hash}: {urllib.parse.quote(analysis_link)}"
        )
        return_list.append(analysis_link)

    return return_list


modules_manager.ModulesManager.RegisterModule(VTCollector)
