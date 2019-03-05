# -*- coding: utf-8 -*-
"""Threat intelligence related attribute container definitions."""

from dftimewolf.lib.datatypes import interface

class ThreatIntelligence(interface.AttributeContainer):
  """Analysis report attribute container.
  Attributes:
    name (string): name of the threat
    indicator (string): regular expression relevant to a threat
  """
  CONTAINER_TYPE = 'threat_intelligence'

  def __init__(self, name, indicator):
    """Initializes the analysis report.
    Args:
      name (string): name of the threat
      indicator (string): regular expression relevant to a threat
    """
    super(ThreatIntelligence, self).__init__()
    self.name = name
    self.indicator = indicator
