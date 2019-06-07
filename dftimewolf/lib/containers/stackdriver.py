# -*- coding: utf-8 -*-
"""Stackdriver related attribute container definitions."""

from dftimewolf.lib.containers import interface

class StackdriverLogs(interface.AttributeContainer):
  """Analysis report attribute container.

  Attributes:
    filter_expression (str): Stackdriver advanced logs filter expression
        used to generate the results.
    path (str): path to a stackdriver log file.
    project_name (str): name of the project that was queried.
  """
  CONTAINER_TYPE = 'stackdriver_logs'

  def __init__(self, path, filter_expression, project_name):
    """Initializes the analysis report.

    Args:
      filter_expression (str): Stackdriver advanced logs filter expression
          used to generate the results.
      path (str): path to a stackdriver log file.
      project_name (str): name of the project that was queried.
    """
    super(StackdriverLogs, self).__init__()
    self.filter_expression = filter_expression
    self.path = path
    self.project_name = project_name
