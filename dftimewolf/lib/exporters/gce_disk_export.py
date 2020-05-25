# -*- coding: utf-8 -*-
"""Export disk image from a GCP project to Google Cloud Storage."""

from __future__ import print_function
from __future__ import unicode_literals

import os
from libcloudforensics import gcp

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class GoogleCloudDiskExport(module.BaseModule):
  """Google Cloud Platform (GCP) Disk Export.

  Attributes:
    analysis_project (gcp.GoogleCloudProject): Project where the disk
         image is created then exported.
         If not exit, source_project will be used.
    source_project (gcp.GoogleCloudProject): Source project
        containing the disk to export.
    source_disk (gcp.GoogleComputeDisk): Disk that needs to be exported.
    gcs_output_location (str): Google Cloud Storage parent bucket/folder
        path of the exported image.
    exported_disk_name (str): Name of the output file, must comply
        with ^[A-Za-z0-9-]*$' and '.tar.gz' will be appended to the name. If not
        exist, random name will be generated.
    _image_name (str): Intermediary image to export.
  """

  def __init__(self, state, critical=False):
    """Initializes a Google Cloud Platform (GCP) Disk Export.

    Args:
      state (DFTimewolfState): recipe state.
      critical (Optional[bool]): True if the module is critical, which causes
          the entire recipe to fail if the module encounters an error.
    """
    super(GoogleCloudDiskExport, self).__init__(state, critical=critical)
    self.analysis_project = None
    self.source_project = None
    self.source_disk = None
    self.gcs_output_location = None
    self.exported_disk_name = None
    self._image_name = None

  def Process(self):
    """Creates and exports disk image to the output bucket."""
    image_object = self.analysis_project.CreateImageFromDisk(
        self.source_disk, name=self._image_name)
    image_object.ExportImage(
        self.gcs_output_location, output_name=self.exported_disk_name)
    image_object.Delete()
    output_uri = os.path.join(
        self.gcs_output_location, '{0:s}.tar.gz'.format(
            self.exported_disk_name))
    print('Disk was exported to: {0:s}'.format(output_uri))
    self.state.output.append(output_uri)

  # pylint: disable=arguments-differ
  def SetUp(self,
            source_project_name,
            source_disk_name,
            gcs_output_location,
            analysis_project_name=None,
            exported_disk_name=None):
    """Sets up a Google Cloud Platform (GCP) Disk Export.

    This method creates the required objects to initialize
    the GoogleCloudDiskExport class attributes.

    If the analysis_project_name is not specified it will use the
    source_project_name instead.

    Args:
      source_project_name (str): Source project ID containing
          the disk to export.
      source_disk_name (str): Disk that needs to be exported.
      gcs_output_location (str): Google Cloud Storage parent bucket/folder
          path of the exported image.
      analysis_project_name (Optional[str]): Project ID where the
          disk image is created then exported. If not exit,
          source_project_name will be used.
      exported_disk_name (Optional[str]): Name of the output file, must comply
          with ^[A-Za-z0-9-]*$' and '.tar.gz' will be appended to the name.
          If not exist, random name will be generated.
    """
    self.source_project = gcp.GoogleCloudProject(source_project_name)
    if analysis_project_name:
      self.analysis_project = gcp.GoogleCloudProject(analysis_project_name)
    else:
      self.analysis_project = self.source_project
    self.source_disk = self.source_project.GetDisk(source_disk_name)
    self.gcs_output_location = gcs_output_location
    self._image_name = '{0:s}-image-df-export-temp'.format(
        self.source_disk.name)
    if exported_disk_name:
      self.exported_disk_name = exported_disk_name
    else:
      self.exported_disk_name = self._image_name

modules_manager.ModulesManager.RegisterModule(GoogleCloudDiskExport)
