# -*- coding: utf-8 -*-
"""Processes artifacts using local grep ."""

import mimetypes
import os
import re
import tempfile

import PyPDF2

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager as modules_manager


class GrepperSearch(module.BaseModule):
  """Processes a list of file paths with to search for
  specific keywords.

  input: A file path to process, and a list of keywords to search for
  output: filepath and keyword match, to stdout (final_output).
  """

  def __init__(self, state):
    super(GrepperSearch, self).__init__(state)
    self._keywords = None
    self._output_path = None
    self._final_output = None

  def SetUp(self, keywords=None):  # pylint: disable=arguments-differ
    """Sets up the _keywords attribute.

    Args:
      keywords (Optional[str]): pipe separated keywords to search
    """
    self._keywords = keywords
    self._output_path = tempfile.mkdtemp()

  def Process(self):
    """Executes grep on the module input."""
    for _, path in self.state.input:
      log_file_path = os.path.join(self._output_path, 'grepper.log')
      print('Log file: {0:s}'.format(log_file_path))

      print('Walking through dir (absolute) = ' + os.path.abspath(path))
      try:
        for root, _, files in os.walk(path):
          for filename in files:
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
                  filter(None, found)))
              if self._final_output:
                self._final_output += '\n' + output
              else:
                self._final_output = output
              print(output)
      except OSError as exception:
        self.state.AddError(str(exception), critical=True)
        return
      # Catch all remaining errors since we want to gracefully report them
      except Exception as exception:  # pylint: disable=broad-except
        self.state.AddError(str(exception), critical=True)
        return

  def GrepPDF(self, path):
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
