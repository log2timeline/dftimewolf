# -*- coding: utf-8 -*-
"""The attribute container interface."""
from typing import Any, Dict, List


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
    attributes: A list of generic attributes that can be used for passing
      metadata between collection/processing module and output modules.
  """
  CONTAINER_TYPE = None  # type: str
  attributes = []  # type: List[Dict[str, Any]]

  def __init__(self, attributes: List[Dict[str, any]] = []):
    """Initializes an AttributeContainer.

    Args:
      attributes: A list of generic attributes that can be used for passing
        metadata between collection/processing module and output modules.
    """
    self.attributes = attributes

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
