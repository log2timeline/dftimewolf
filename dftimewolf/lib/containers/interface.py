# -*- coding: utf-8 -*-
"""The attribute container interface."""

from typing import Any, Dict, List, Optional

import pandas as pd


METADATA_KEY_SOURCE_MODULE = "SOURCE_MODULE"


class AttributeContainer():
  """The attribute container interface.

  This is the base class for those object that exists primarily as
  a container of attributes with basic accessors and mutators.

  The CONTAINER_TYPE class attribute contains a string that identifies
  the container type e.g. the container type "event" identifies an event
  object.

  Attributes are public class members of an serializable type. Protected
  and private class members are not to be serialized.

  Attributes:
    metadata: A dict of container metadata that can be used for passing
      metadata between collection/processing module and output modules.
  """
  CONTAINER_TYPE = None  # type: str
  metadata = {}  # type: Dict[str, Any]

  def __init__(self, metadata: Optional[Dict[str, Any]] = None):
    """Initializes an AttributeContainer.

    Args:
    metadata: A dict of container metadata that can be used for passing
      metadata between collection/processing module and output modules.
    """
    if metadata is None:
      self.metadata = {}
    else:
      self.metadata = metadata

  # TODO: note that this method is only used by tests.
  def GetAttributeNames(self) -> List[str]:
    """Retrieves the names of all attributes.

    Returns:
      list[str]: attribute names.
    """
    attribute_names = []
    for attribute_name in iter(self.__dict__.keys()):
      # Not using startswith to improve performance.
      if attribute_name[0] == '_':
        continue
      attribute_names.append(attribute_name)

    return attribute_names

  def SetMetadata(self, key: str, value: Any) -> None:
    """Sets metadata to the container.

    Args:
      key: Metadata key
      value: Metadata value
    """
    self.metadata[key] = value

  def __eq__(self, other: "AttributeContainer") -> bool:
    """Override the `==` operator. Equality ignores metadata."""
    if self.CONTAINER_TYPE != other.CONTAINER_TYPE:
      return False
    for k, v in self.__dict__.items():
      if k == 'metadata':
        continue
      if k not in other.__dict__:
        return False

      # Edge case for child classes that have Dataframe members, which cannot
      # be compared with `==`. We do this here, so every child class that has
      # a dataframe doesn't have to reimplement this method.
      if (isinstance(v, pd.DataFrame) or
          isinstance(other.__dict__[k], pd.DataFrame)):
        if v is None or other.__dict__[k] is None:
          return False
        if not v.equals(other.__dict__[k]):
          return False
      else:
        if other.__dict__[k] != v:
          return False
    return True
