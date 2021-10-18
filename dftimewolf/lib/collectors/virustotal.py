# -*- coding: utf-8 -*-
"""Downloads several items for a VT file."""

import os
import tempfile
import zipfile

from typing import List
from typing import Optional

import vt

from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.state import DFTimewolfState


class VTCollector(module.BaseModule):
  """Virustotal (VT) Collector.

  Attributes:
    - hashes_list List[hashes_list]: List of hashes passed ot the module
    - vt_type: pcap or evtx depending on the file type requested

  """

  def __init__(
      self,
      state: DFTimewolfState,
      name: Optional[str],
      critical: bool = False) -> None:
    """Initializes an Virustotal (VT) collector.

    Args:
      state (DFTimewolfState): recipe state.
      name (Optional): The module's runtime name.
      critical (Optional): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(VTCollector, self).__init__(state, name=name, critical=critical)
    self.hashes_list: List[str] = []
    self.output_path: Optional[str] = None
    self.client: Optional[vt.Client] = None
    self.vt_type = None

  def Process(self) -> None:
    """Not implemented yet"""

    for vt_hash in self.hashes_list:
      if not self._isHashKnownToVT(vt_hash):
        self.logger.info(
            'Hash not found on VT removing element {0:s} from list'.format(
                vt_hash))
        self.hashes_list.remove(vt_hash)

    self.logger.info(
        'Found the following files on VT: {0:s}'.format(*self.hashes_list))

    for vt_hash in self.hashes_list:
      pcap_download_list = self._get_download_links(vt_hash)

    for download_link in pcap_download_list:
      self.logger.info(download_link)
      real = f"{download_link}/{self.vt_type}"
      filepath = f'{download_link.rsplit("/", 1)[-1]}.{self.vt_type}'
      file = open(filepath, "wb")

      download = self.client.get(real)
      if download.status == 200:
        file.write(download.content.read())

        # In case the provided PCAP is size 0, delete the file and move on
        if os.stat(filepath).st_size == 0:
          if os.path.exists(filepath):
            os.remove(filepath)
            continue
      else:
        self.ModuleError(f"File not found {real}", critical=False)

      if self.vt_type == 'pcap':
        self.logger.info('Writing pcap to file')

        container = containers.File(
            name=vt_hash, path=os.path.abspath(filepath))
        self.state.StoreContainer(container)
        self.logger.info('Finished writing evtx to file')

      if self.vt_type == 'evtx':
        self.logger.info('Writing evtx to file')

        # Unzip the file so that plaso can go over evtx part in the archive
        client_output_file = os.path.join(self.output_path, vt_hash)
        if not os.path.isdir(client_output_file):
          os.makedirs(client_output_file)

        with zipfile.ZipFile(filepath) as archive:
          archive.extractall(path=client_output_file)
          self.logger.debug(
              'Downloaded file extracted to {0:s}'.format(client_output_file))

        container = containers.File(
            name=vt_hash, path=os.path.abspath(client_output_file))
        self.state.StoreContainer(container)
        self.logger.info('Finished writing evtx to file')

  # pylint: disable=arguments-differ,too-many-arguments
  def SetUp(
      self,
      hashes: str,
      vt_api_key: str,
      vt_type: str,
      output_path: str = tempfile.mkdtemp(),
  ) -> None:
    """Sets up an Virustotal (VT) collector.

    Args:
      hashes: Coma seperated strings of hashes
      vt_api_key: Virustotal Enterprise API Key
      vt_type: Which file to fetch
      output_path [optional]: Where to store the downloaded files to
    """

    self.output_path = self._CheckOutputPath(output_path)

    if not hashes:
      self.ModuleError("You need to specify at least one hash", critical=True)
      return

    if not vt_type:
      self.ModuleError(
          "You need to specify an vt_type from: pcap, evtx", critical=True)
      return

    self.vt_type = vt_type

    self.hashes_list = [item.strip() for item in hashes.strip().split(",")]

    if not vt_api_key:
      self.ModuleError(
          "You need to specify a Virustotal Enterprise API key",
          critical=True,
      )
      return

    self.client = vt.Client(vt_api_key)

    if self.client is None:
        self.ModuleError(
            f'Error creating Virustotal Client instance',
            critical=True,
        )
        return

  def _Store_filepath_to_pandas(
      self, filepath: str, vt_hash: str,
      download_link: str) -> containers.DataFrame:
    """ Returns a pandas container """
    """
    frame = self._pcap_to_pandas(filepath)

    if frame is None:
      self.logger.error(
          'Found empty Pandas for {0:s} {1:s}'.format(vt_hash, download_link))
      return None  # we do not want to kill the whole loop
    container = containers.DataFrame(
        data_frame=frame,
        description=f'PCAP2Pandas for hash {vt_hash} {download_link}',
        name=f'PCAP_{vt_hash}',
    )
    return container
    """
    raise NotImplementedError

  def _CheckOutputPath(self, output_path: str = tempfile.mkdtemp()) -> str:
    """Checks that the output path can be manipulated by the module.

    Args:
    output_path: Full path to the output directory where files will be
        dumped.

    Returns:
        The full path to the directory where files will be dumped.
    """
    # Check that the output path can be manipulated
    if not output_path:
      return tempfile.mkdtemp()
    elif os.path.exists(output_path):
      return output_path
    elif not os.path.exists(output_path):
      try:
        os.makedirs(output_path)
        return output_path
      except OSError as error:
        self.ModuleError(
            "{0:s} error while creating the output directory: {1!s}".format(
                output_path, error),
            critical=True,
        )
        """Below should never be reached, but Either all return statements in 
        a function should return an expression, or none of them should. 
        (inconsistent-return-statements)
        """
        return tempfile.mkdtemp()
    elif not os.path.isdir(output_path):
      self.ModuleError(output_path + " is not a directory:", critical=True)
      return tempfile.mkdtemp()
    else:
      return tempfile.mkdtemp()

  def _isHashKnownToVT(self, vt_hash: str) -> bool:
    """Checks if a hash is known to VT.

          Args:
              vt_hash ([str]): A hash.

          Returns:
              Bool: True if found on VT
              False: File not found on VT.
          """
    try:
      self.logger.debug(f'Trying to find {vt_hash} on Virustotal...')
      self.client.get_object(f"/files/{vt_hash}")
    except:  # pylint: disable=bare-except
      return False

    return True

  def _get_download_links(self, vt_hash: str, ) -> List[str]:
    """Checks if a hash has a PCAP file available.
    Returns a list of the URLs for download.
    One hash can have multiple PCAPs available.

    Args:
        vt_hash: A hash.

    Returns:
        list[str]: List of strings with URLs to the PCAP files.
    """
    vt_data = self.client.get_data(f"/files/{vt_hash}/behaviours")
    return_list = []
  
    for analysis in vt_data:
      if analysis["attributes"][f'has_{self.vt_type}']:
        analysis_link = analysis["links"]["self"]
        self.logger.info(
            'Found PCAP for {0:s} to be processed: {1:s}'.format(
                vt_hash, analysis_link))
        return_list.append(analysis_link)

    return return_list


modules_manager.ModulesManager.RegisterModule(VTCollector)
