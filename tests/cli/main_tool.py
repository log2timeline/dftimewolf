#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the main tool functionality."""

import unittest
import logging

from dftimewolf.cli import dftimewolf_recipes


class MainToolTest(unittest.TestCase):
  """Tests for main tool functions."""

  def setUp(self):
    pass

  def testSetupLogging(self):
    """Tests the SetupLogging function."""
    dftimewolf_recipes.SetupLogging()
    logger = logging.getLogger('dftimewolf')
    root_logger = logging.getLogger()
    self.assertEqual(len(logger.handlers), 2)
    self.assertEqual(len(root_logger.handlers), 1)
