# -*- coding: utf-8 -*-
"""Processes artifacts using local grep ."""
from __future__ import print_function
from __future__ import unicode_literals

import os
import tempfile
import re
import mimetypes
import PyPDF2

from dftimewolf.lib.module import BaseModule


class GrepperSearch(BaseModule):
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

  def setup(self, keywords=None):  # pylint: disable=arguments-differ
    """Sets up the _keywords attribute.

    Args:
      keywords: pipe separated list of keyword to search
    """
    self._keywords = keywords
    self._output_path = tempfile.mkdtemp()

  def cleanup(self):
    pass

  def process(self):
    """Execute the grep command"""

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
              found = self.grepPDF(fullpath)
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
      except OSError as error:
        self.state.add_error(str(error), critical=True)
        return
      # Catch all remaining errors since we want to gracefully report them
      except Exception as error:  # pylint: disable=broad-except
        self.state.add_error(str(error), critical=True)
        return

  def grepPDF(self, path):
    """
    Parse PDF files text content for keywords.

    Args:
      path: PDF file path.

    Returns:
      match: set of unique occurrences of every match.
    """
    with open(path, 'rb') as pdf_file_obj:
      match = set()
      text = ''
      pdf_reader = PyPDF2.PdfFileReader(pdf_file_obj)
      pages = pdf_reader.numPages
      for page in range(pages):
        page_obj = pdf_reader.getPage(page)
        text += '\n' + page_obj.extractText()
      match.update(set(x.lower() for x in re.findall(
          self._keywords, text, re.IGNORECASE)))
    return match
