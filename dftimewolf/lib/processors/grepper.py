# -*- coding: utf-8 -*-
"""Processes artifacts using local grep ."""

import mimetypes
import os
import re
import tempfile
from typing import TYPE_CHECKING, Optional, Set

import PyPDF2

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager
from dftimewolf.lib.containers import containers


if TYPE_CHECKING:
  from dftimewolf.lib import state
  from dftimewolf.lib.containers import interface

class GrepperSearch(module.BaseModule):
  """Processes a list of file paths with to search for
  specific keywords.

  input: A file path to process, and a list of keywords to search for
  output: filepath and keyword match, to stdout (final_output).
  """

  def __init__(self,
               state: "state.DFTimewolfState",
               name: Optional[str]=None,
               critical: bool=False):

    super(GrepperSearch, self).__init__(state, name=name, critical=critical)
    self._keywords: str
    self._output_path: str
    self._final_output = ''

  def SetUp(self, keywords: str) -> None:  # pylint: disable=arguments-differ
    """Sets up the _keywords attribute.

    Args:
      keywords (str): pipe separated keywords to search
    """
    self._keywords = keywords
    self._output_path = tempfile.mkdtemp()

  def Process(self) -> None:
    """Executes grep on the module input."""
    for file_container in self.state.GetContainers(containers.File):
      path = file_container.path
      log_file_path = os.path.join(self._output_path, 'grepper.log')
      self.logger.info('Log file: {0:s}'.format(log_file_path))

      self.logger.info('Walking through dir (absolute) = {0:s}'.format(
          os.path.abspath(path)))
      try:
        for root, _, files in os.walk(path):
          for filename in sorted(files):
            found = set()
            fullpath = '{0:s}/{1:s}'.format(os.path.abspath(root), filename)
            if mimetypes.guess_type(filename)[0] == 'application/pdf':
              found = self.GrepPDF(fullpath)
            else:
              with open(fullpath, 'r') as fp:
                for line in fp:
                  found.update(set(x.lower() for x in re.findall(
                      self._keywords, line, re.IGNORECASE)))
            if [item for item in found if item]:
              output = '{0:s}/{1:s}:{2:s}'.format(path, filename, ','.join(
                  filter(None, sorted(found))))
              if self._final_output:
                self._final_output += '\n' + output
              else:
                self._final_output = output
              self.logger.info(output)
      except OSError as exception:
        self.ModuleError(str(exception), critical=True)
      # Catch all remaining errors since we want to gracefully report them

  def GrepPDF(self, path:str) -> Set[str]:
    """Parses a PDF files text content for keywords.

    Args:
      path (str): PDF file path.

    Returns:
      set[str]: unique occurrences of every match.
    """
    with open(path, 'rb') as pdf_file_obj:
      matches = set()
      text = ''
      pdf_reader = PyPDF2.PdfFileReader(pdf_file_obj)
      pages = pdf_reader.numPages
      for page in range(pages):
        page_obj = pdf_reader.getPage(page)
        text += '\n' + page_obj.extractText()
      matches.update(set(x.lower() for x in re.findall(
          self._keywords, text, re.IGNORECASE)))
    return matches


modules_manager.ModulesManager.RegisterModule(GrepperSearch)
