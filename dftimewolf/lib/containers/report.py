# -*- coding: utf-8 -*-
"""Report related attribute container definitions."""

from dftimewolf.lib.containers import interface

class Report(interface.AttributeContainer):
  """Analysis report attribute container.
  Attributes:
    module_name (str): name of the module that generated the report.
    text (str): report text.
  """
  CONTAINER_TYPE = 'report'

  def __init__(self, module_name, text):
    """Initializes the analysis report.
    Args:
      module_name (str): name of the analysis plugin that generated
          the report.
      text (str): report text.
    """
    super(Report, self).__init__()
    self.module_name = module_name
    self.text = text
