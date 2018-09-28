# -*- coding: utf-8 -*-
"""Processes artifacts using local grep ."""
from __future__ import print_function
from __future__ import unicode_literals

import os
import subprocess
import tempfile

from dftimewolf.lib.module import BaseModule


class GrepperSearch(BaseModule):
  """Processes a list of file paths with egrep to search for
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

    for description, path in self.state.input:
      log_file_path = os.path.join(self._output_path, 'triager.log')
      print('Log file: {0:s}'.format(log_file_path))

      # Build the grep command line.
      cmd = ['egrep', '-roi', self._keywords, path]
      cmd_sort = ['sort', '-u']

      # Run the grep command
      full_cmd = ' '.join(cmd)
      print('Running external command: "{0:s}"'.format(full_cmd))
      try:
        grep_proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sort_proc = subprocess.Popen(
            cmd_sort, stdin=grep_proc.stdout, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        self._final_output, error = sort_proc.communicate()
        grep_status = grep_proc.wait()
        sort_status = sort_proc.wait()
        print("\nKeyword matching output:")
        print(self._final_output)
        if grep_status:
          # self.console_out.StdErr(errors)
          message = ('The egrep command {0:s} failed: {1:s}.'
                     ' Check log file for details.').format(full_cmd, error)
          self.state.add_error(message, critical=True)

        if sort_status:
          # self.console_out.StdErr(errors)
          message = ('The sort command {0:s} failed: {1:s}.'
                     ' Check log file for details.').format(cmd_sort, error)
          self.state.add_error(message, critical=True)
        self.state.output.append((description, log_file_path))
      except OSError as exception:
        self.state.add_error(exception, critical=True)
      # Catch all remaining errors since we want to gracefully report them
      except Exception as exception:  # pylint: disable=broad-except
        self.state.add_error(exception, critical=True)
