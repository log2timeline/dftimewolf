# -*- coding: utf-8 -*-
"""Modules manager class."""

class ModulesManager(object):
  """Modules manager."""

  # Allow a previously registered module to be overridden.
  ALLOW_MODULE_OVERRIDE = False

  _module_classes = {}

  @classmethod
  def DeregisterModule(cls, module_class):
    """Deregisters a module class.

    The module classes are identified based on their class name.

    Args:
      module_class (type): class of the module, which is a subclass of
          BaseModule.

    Raises:
      KeyError: if module class is not set for the corresponding class name.
    """
    class_name = module_class.__name__
    if class_name not in cls._module_classes:
      raise KeyError('Module class not set for: {0:s}.'.format(class_name))

    del cls._module_classes[class_name]

  @classmethod
  def GetModuleByName(cls, name):
    """Retrieves a specific by its name.

    Args:
      name (str): name of the module.

    Returns:
      type: the module class, which is a subclass of BaseModule, or None if
          no corresponding module was found.
    """
    return cls._module_classes.get(name, None)

  @classmethod
  def RegisterModule(cls, module_class):
    """Registers a module class.

    The module classes are identified based on their class name.

    Args:
      module_class (type): class of the module, which is a subclass of
          BaseModule.

    Raises:
      KeyError: if module class is already set for the corresponding class name.
    """
    class_name = module_class.__name__
    if class_name in cls._module_classes and not cls.ALLOW_MODULE_OVERRIDE:
      raise KeyError('Module class already set for: {0:s}.'.format(class_name))

    cls._module_classes[class_name] = module_class

  @classmethod
  def RegisterModules(cls, module_classes):
    """Registers module classes.

    The module classes are identified based on their class name.

    Args:
      module_classes (list[type]): classes of the modules, which are subclasses
          of BaseModule.

    Raises:
      KeyError: if module class is already set for the corresponding class name.
    """
    for module_class in module_classes:
      cls.RegisterModule(module_class)
