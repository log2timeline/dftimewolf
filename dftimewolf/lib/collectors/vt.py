# -*- coding: utf-8 -*-
"""Downloads several items for a VT file."""

import datetime
import os
import tempfile
from typing import List

import numpy as np
import pandas as pd
import pytz
from dftimewolf.lib import module
from dftimewolf.lib.containers import containers
from dftimewolf.lib.modules import manager as modules_manager
from scapy import all as scapy_all

import vt


class VTCollector(module.BaseModule):
    """Virustotal (VT) Collector.

    Attributes:

    """

    def __init__(self, state, name=None, critical=False) -> None:
        """Initializes an Virustotal (VT) collector.

        Args:
          state (DFTimewolfState): recipe state.
          name (Optional[str]): The module's runtime name.
          critical (Optional[bool]): True if the module is critical, which causes
              the entire recipe to fail if the module encounters an error.
        """
        super(VTCollector, self).__init__(state, name=name, critical=critical)
        self.client = None
        self.hashes = None
        self.output_path = None

    def Process(self) -> None:
        """Not implemented yet"""
        print("Not implemented")

    # pylint: disable=arguments-differ,too-many-arguments
    def SetUp(self, hashes: str, vt_api_key: str, type: str = 'pcap', action: str = 'download', output_path: typing.Optional[str] = None) -> None:
        """Sets up an Virustotal (VT) collector.

        Args:
          hashes (str): Coma seperated strings of hashes
          vt_api_key (str): Virustotal Enterprise API Key
          type (str): One of [pcap] - can be extended if more filetypes can be downloaded
          action (str) : Which action to execute
          output_path [optional] (str) : Where to store the downloaded files to
        """

        self.output_path = self._CheckOutputPath(output_path)

        if not (hashes):
            self.ModuleError(
                'You need to specify at least one hash',
                critical=True)
            return

        if not action:
            self.ModuleError(
                'You need to specify an action from: pcap',
                critical=True)
            return

        self.hashes = [item.strip() for item in hashes.strip().split(',')]

        if not (vt_api_key):
            self.ModuleError(
                'You need to specify a Virustotal Enterprise API key',
                critical=True)
            return

        self.client = vt.Client(vt_api_key)

        for vt_hash in self.hashes:
            if not self._isHashKnownToVT(vt_hash):
                self.logger.info(
                    f'Hash not found on VT removing element {vt_hash} from list')
                self.hashes.remove(vt_hash)

        self.logger.info(f'Found the following files on VT: {self.hashes}')

        if type == 'pcap':
            for vt_hash in self.hashes:
                pcap_download_list = self._get_pcap_download_links(vt_hash)
        else:
            self.ModuleError(
                f'Type: {type} not implemented in Virustotal Module - ending',
                critical=True)
            return

        for download_link in pcap_download_list:
            self.logger.info(download_link)
            real = f'{download_link}/pcap'
            filepath = f'{download_link.rsplit("/", 1)[-1]}.pcap'
            file = open(filepath, "wb")

            download = self.client.get(real)
            if download.status == 200:
                file.write(download.content.read())
                file.close

                # In case the provided PCAP is size 0, delete the file and move on
                if os.stat(filepath).st_size == 0:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        continue
            else:
                self.ModuleError(
                    f'File not found {real}',
                    critical=False)

            frame = self._pcap_to_pandas(filepath)

            if frame is None:
                self.logger.error(
                    f'Found empty Pandas for {vt_hash} {download_link}')
                continue
            container = containers.DataFrame(
                data_frame=frame, description=f'PCAP2Pandas DFTimewolf for hash {vt_hash} {download_link}', name=f'PCAP_{vt_hash}')
            self.state.StoreContainer(container)

    def _CheckOutputPath(self, output_path: typing.Optional[str] = None) -> str:
        """Checks that the output path can be manipulated by the module.

        Args:
        output_path: Full path to the output directory where files will be
            dumped.

        Returns:
            str: The full path to the directory where files will be dumped.
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
                    '{0:s} error while creating the output directory: {1!s}'.format(
                        output_path, error), critical=True)
        elif not os.path.isdir(output_path):
            self.ModuleError(
                output_path + ' is not a directory:', critical=True)
        else:
            return tempfile.mkdtemp()

        return output_path

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
            self.client.get_object(f'/files/{vt_hash}')
        except:
            return False

        return True

    def _get_pcap_download_links(self, vt_hash: str) -> List[str]:
        """Checks if a hash has a PCAP file available and returns a list of the URLs for download.
        One hash can have multiple PCAPs available.

        Args:
            vt_hash ([str]): A hash.

        Returns:
            list[str]: List of strings with URLs to the PCAP files.
        """
        vt_data = self.client.get_data(
            f'/files/{vt_hash}/behaviours')
        return_list = []
        for analysis in vt_data:
            if analysis['attributes']['has_pcap']:
                analysis_link = analysis['links']['self']
                self.logger.info(
                    f'Found PCAP for {vt_hash} appending it to the process queue: {analysis_link}')
                return_list.append(analysis_link)

        return return_list

    def _pcap_to_pandas(self, path: str) -> pd.DataFrame:
        """Reads a PCAP from path and converts it to a Pandas Dataframe.

        Args:
            path ([str]): Path to pcap file to read.

        Returns:
            Pandas Dataframe: Parsed Pandas Dateframe.
        """
        packets = scapy_all.rdpcap(path)

        # @markdown Collect field names from IP/TCP/UDP
        # @markdown *These will be columns in DF*
        ip_fields = [(field.name) for field in scapy_all.IP().fields_desc]
        tcp_fields = [(field.name)
                      for field in scapy_all.TCP().fields_desc]
        udp_fields = [(field.name)
                      for field in scapy_all.UDP().fields_desc]

        ip_fields_new = [("ip_"+field.name)
                         for field in scapy_all.IP().fields_desc]
        tcp_fields_new = [("tcp_"+field.name)
                          for field in scapy_all.TCP().fields_desc]
        udp_fields_new = [("udp_"+field.name)
                          for field in scapy_all.UDP().fields_desc]

        dataframe_fields = ip_fields_new + ['time'] + \
            tcp_fields_new + ['payload', 'datetime', 'raw']

        for packet in packets[scapy_all.IP]:
            # Field array for each row of DataFrame

            field_values: List[str] = []
            # Add all IP fields to dataframe
            for field in ip_fields:
                if field == 'options':
                    # Retrieving number of options defined in IP Header
                    field_values.append(
                        len(packet[scapy_all.IP].fields[field]))
                else:
                    field_values.append(packet[scapy_all.IP].fields[field])

            field_values.append(packet.time)
            layer_type = type(packet[scapy_all.IP].payload)
            for field in tcp_fields:
                try:
                    if field == 'options':
                        field_values.append(
                            len(packet[layer_type].fields[field]))
                    else:
                        field_values.append(
                            packet[layer_type].fields[field])
                except:
                    field_values.append(None)

            # Append payload
            field_values.append(len(packet[layer_type].payload))

            date_value = datetime.datetime.fromtimestamp(
                packet.time, tz=pytz.utc)
            field_values.append(date_value.isoformat())
            field_values.append(str(packet.show2))

            # Create a dict and upload it to timesketch.
            packet_dict = dict(zip(dataframe_fields, field_values))
            ip_flags = packet_dict.get('ip_flags')
            if not ip_flags is None:
                packet_dict['ip_flags'] = ip_flags.names

            tcp_flags = packet_dict.get('tcp_flags')
            if not tcp_flags is None:
                packet_dict['tcp_flags'] = tcp_flags.names

            del packet_dict['time']

            return pd.DataFrame.from_dict(packet_dict)


modules_manager.ModulesManager.RegisterModule(VTCollector)