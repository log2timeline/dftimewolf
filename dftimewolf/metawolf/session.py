#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Metawolf session settables."""

from typing import Any


class SessionSettable:
  """SessionSettable represents a settable attribute for a given session.

  Attributes:
    session_id (str): The session ID this settable belongs to.
    recipe (str): The recipe this settable belongs to.
    name (str): The name of the settable.
    description (str): A description for the settable.
    value_type (Any): The type of the settable's value.
    optional (bool): True if the settable's value is optional.
  """
  def __init__(
      self,
      session_id: str,
      recipe: str,
      name: str,
      description: str,
      value_type: Any,
      optional: bool = False
  ) -> None:
    """Initialize the settable.

    Args:
      session_id (str): The session ID this settable belongs to.
      recipe (str): The recipe this settable belongs to.
      name (str): The name of the settable.
      description (str): A description for the settable.
      value_type (Any): Type that this Settable accepts.
      optional (bool): Optional. True if this is an optional settable.
    """
    self.session_id = session_id
    self.recipe = recipe
    self.name = name
    self.description = description
    self.type = value_type
    self.optional = optional
    self._value = None

  def SetSessionID(self, session_id: str) -> None:
    """Set the settable' session ID.

    Args:
      session_id (str): The session ID for the settable.
    """
    self.session_id = session_id

  def IsOptional(self) -> bool:
    """Return whether or not this is an optional settable."""
    return self.optional

  def SetValue(self, value: Any) -> None:
    """Set the settable' value.

    Args:
      value (Any): The value for the settable.
    """
    self._value = value

  def GetValue(self) -> Any:
    """Return the settable' value."""
    return self._value
