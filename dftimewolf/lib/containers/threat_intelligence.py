# -*- coding: utf-8 -*-
"""Threat intelligence related attribute container definitions."""

from dftimewolf.lib.containers import interface

class ThreatIntelligence(interface.AttributeContainer):
  """Threat Intelligence attribute container.

  Attributes:
    name (string): name of the threat
    indicator (string): regular expression relevant to a threat
  """
  CONTAINER_TYPE = 'threat_intelligence'

  def __init__(self, name, indicator):
    """Initializes the Threat Intelligence container.

    Args:
      name (string): name of the threat
      indicator (string): regular expression relevant to a threat
    """
    super(ThreatIntelligence, self).__init__()
    self.name = name
    self.indicator = indicator
