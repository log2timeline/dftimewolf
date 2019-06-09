# -*- coding: utf-8 -*-
"""Modules manager class."""

from __future__ import unicode_literals


class ModulesManager(object):
  """Modules manager."""

  _module_classes = {}

  @classmethod
  def DeregisterModule(cls, module_class):
    """Deregisters a module class.

    The module classes are identified based on their class name.

    Args:
      module_class (type): class of the module.

    Raises:
      KeyError: if module class is not set for the corresponding class name.
    """
    class_name = module_class.__name__
    if class_name not in cls._module_classes:
      raise KeyError('Module class not set for: {0:s}.'.format(class_name))

    del cls._module_classes[class_name]

  @classmethod
  def RegisterModule(cls, module_class):
    """Registers a module class.

    The module classes are identified based on their class name.

    Args:
      module_class (type): class of the module.

    Raises:
      KeyError: if module class is already set for the corresponding class name.
    """
    class_name = module_class.__name__
    if class_name in cls._module_classes:
      raise KeyError('Module class already set for: {0:s}.'.format(class_name))

    cls._module_classes[class_name] = module_class

  @classmethod
  def RegisterModules(cls, module_classes):
    """Registers module classes.

    The module classes are identified based on their class name.

    Args:
      module_classes (list[type]): classes of the modules.

    Raises:
      KeyError: if module class is already set for the corresponding class name.
    """
    for module_class in module_classes:
      cls.RegisterModule(module_class)
