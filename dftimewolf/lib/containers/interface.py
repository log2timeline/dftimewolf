# -*- coding: utf-8 -*-
"""The attribute container interface."""
from typing import Any, Dict, List, Optional


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
