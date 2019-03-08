# -*- coding: utf-8 -*-
"""The attribute container interface."""
from __future__ import unicode_literals

import six


class AttributeContainerIdentifier(object):
  """The attribute container identifier.
  The identifier is used to uniquely identify attribute containers.
  The value should be unique at runtime and in storage.
  """

  def __init__(self):
    """Initializes an attribute container identifier."""
    super(AttributeContainerIdentifier, self).__init__()
    self._identifier = id(self)

  def copy_to_string(self):
    """Copies the identifier to a string representation.
    Returns:
      str: unique identifier or None.
    """
    return '{0:d}'.format(self._identifier)


class AttributeContainer(object):
  """The attribute container interface.
  This is the base class for those object that exists primarily as
  a container of attributes with basic accessors and mutators.
  The CONTAINER_TYPE class attribute contains a string that identifies
  the container type e.g. the container type "event" identifiers an event
  object.
  Attributes are public class members of an serializable type. Protected
  and private class members are not to be serialized.
  """
  CONTAINER_TYPE = None

  def __init__(self):
    """Initializes an attribute container."""
    super(AttributeContainer, self).__init__()
    self._identifier = AttributeContainerIdentifier()
    self._session_identifier = None

  def copy_from_dict(self, attributes):
    """Copies the attribute container from a dictionary.
    Args:
      attributes (dict[str, object]): attribute values per name.
    """
    for attribute_name, attribute_value in attributes.items():
      # Not using startswith to improve performance.
      if attribute_name[0] == '_':
        continue
      setattr(self, attribute_name, attribute_value)

  def copy_to_dict(self):
    """Copies the attribute container to a dictionary.
    Returns:
      dict[str, object]: attribute values per name.
    """
    return {
        attribute_name: attribute_value
        for attribute_name, attribute_value in self.get_attributes()}

  def get_attribute_names(self):
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

  def get_attributes(self):
    """Retrieves the attribute names and values.
    Attributes that are set to None are ignored.
    Yields:
      tuple[str, object]: attribute name and value.
    """
    for attribute_name, attribute_value in iter(self.__dict__.items()):
      # Not using startswith to improve performance.
      if attribute_name[0] == '_' or attribute_value is None:
        continue

      yield attribute_name, attribute_value

  def get_attribute_values_hash(self):
    """Retrieves a comparable string of the attribute values.
    Returns:
      int: hash of comparable string of the attribute values.
    """
    return hash(self.get_attribute_values_string())

  def get_attribute_values_string(self):
    """Retrieves a comparable string of the attribute values.
    Returns:
      str: comparable string of the attribute values.
    """
    attributes = []
    for attribute_name, attribute_value in sorted(self.__dict__.items()):
      # Not using startswith to improve performance.
      if attribute_name[0] == '_' or attribute_value is None:
        continue

      if isinstance(attribute_value, dict):
        attribute_value = sorted(attribute_value.items())

      elif isinstance(attribute_value, six.binary_type):
        attribute_value = repr(attribute_value)

      attribute_string = '{0:s}: {1!s}'.format(attribute_name, attribute_value)
      attributes.append(attribute_string)

    return ', '.join(attributes)

  def get_identifier(self):
    """Retrieves the identifier.
    The identifier is a storage specific value that should not be serialized.
    Returns:
      AttributeContainerIdentifier: an unique identifier for the container.
    """
    return self._identifier

  def get_session_identifier(self):
    """Retrieves the session identifier.
    The session identifier is a storage specific value that should not
    be serialized.
    Returns:
      str: session identifier.
    """
    return self._session_identifier

  def set_identifier(self, identifier):
    """Sets the identifier.
    The identifier is a storage specific value that should not be serialized.
    Args:
      identifier (AttributeContainerIdentifier): identifier.
    """
    self._identifier = identifier

  def set_session_identifier(self, session_identifier):
    """Sets the session identifier.
    The session identifier is a storage specific value that should not
    be serialized.
    Args:
      session_identifier (str): session identifier.
    """
    self._session_identifier = session_identifier
