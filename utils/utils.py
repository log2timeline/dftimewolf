# -*- coding: utf-8 -*-
"""Helper to load files from utils."""

import os


def ReadExportScript(filename: str) -> str:
    """Reads the Startup script used to export disks to GCS.

    This is stored at utils/export_machine_startup_script.sh

    Args:
      filename: name of the file to read.

    Raises:
      OSError: If the script cannot be opened, read or closed.
    """
    try:
      path = os.path.join(
          os.path.dirname(os.path.realpath(__file__)), filename)
      with open(path, encoding='utf-8') as startup_script:
        return startup_script.read()
    except OSError as exception:
      raise OSError(
          'Could not open/read/close the Export script {0:s}: {1:s}'.format(
              path, str(exception))) from exception
