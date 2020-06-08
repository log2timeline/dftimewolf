#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the modules manager."""

import unittest

from dftimewolf.lib import module
from dftimewolf.lib.modules import manager


class TestModule(module.BaseModule):  # pylint: disable=abstract-method
  """Test module."""


class ModulesManagerTest(unittest.TestCase):
  """Tests for the modules manager."""

  # pylint: disable=protected-access

  def setUp(self):
    manager.ModulesManager.ALLOW_MODULE_OVERRIDE = False

  def testModuleRegistration(self):
    """Tests the RegisterModule and DeregisterModule functions."""
    number_of_module_classes = len(manager.ModulesManager._module_classes)

    manager.ModulesManager.RegisterModule(TestModule)
    self.assertEqual(
        len(manager.ModulesManager._module_classes),
        number_of_module_classes + 1)

    with self.assertRaises(KeyError):
      manager.ModulesManager.RegisterModule(TestModule)

    manager.ModulesManager.DeregisterModule(TestModule)
    self.assertEqual(
        len(manager.ModulesManager._module_classes), number_of_module_classes)

  def testOverrideModuleRegistration(self):
    """Tests the RegisterModule with override functionality."""
    manager.ModulesManager.ALLOW_MODULE_OVERRIDE = True
    number_of_module_classes = len(manager.ModulesManager._module_classes)

    manager.ModulesManager.RegisterModule(TestModule)
    self.assertEqual(
        len(manager.ModulesManager._module_classes),
        number_of_module_classes + 1)

    # Registering the same module twice should not raise an exception.
    manager.ModulesManager.RegisterModule(TestModule)
    self.assertEqual(
        len(manager.ModulesManager._module_classes),
        number_of_module_classes + 1)

    manager.ModulesManager.DeregisterModule(TestModule)
    self.assertEqual(
        len(manager.ModulesManager._module_classes), number_of_module_classes)

  # TODO: add tests for GetModuleByName

  def testRegisterModules(self):
    """Tests the RegisterModules function."""
    number_of_module_classes = len(manager.ModulesManager._module_classes)

    manager.ModulesManager.RegisterModules([TestModule])
    self.assertEqual(
        len(manager.ModulesManager._module_classes),
        number_of_module_classes + 1)

    manager.ModulesManager.DeregisterModule(TestModule)


if __name__ == '__main__':
  unittest.main()
