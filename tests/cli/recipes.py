#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the local filesystem collector."""

from __future__ import unicode_literals

import unittest
import six

from dftimewolf.cli.recipes import artifact_grep
from dftimewolf.cli.recipes import gcp_turbinia_import
from dftimewolf.cli.recipes import gcp_turbinia
from dftimewolf.cli.recipes import grr_artifact_hosts
from dftimewolf.cli.recipes import grr_fetch_files
from dftimewolf.cli.recipes import grr_flow_download
from dftimewolf.cli.recipes import grr_hunt_artifacts
from dftimewolf.cli.recipes import grr_hunt_file
from dftimewolf.cli.recipes import grr_huntresults_plaso_timesketch
from dftimewolf.cli.recipes import local_plaso
from dftimewolf.cli.recipes import timesketch_upload

class RecipeTests(unittest.TestCase):
  """Tests for recipe construction."""

  def setUp(self):
    self.recipes = [
        artifact_grep,
        gcp_turbinia_import,
        gcp_turbinia,
        grr_artifact_hosts,
        grr_fetch_files,
        grr_flow_download,
        grr_hunt_artifacts,
        grr_hunt_file,
        grr_huntresults_plaso_timesketch,
        local_plaso,
        timesketch_upload,
    ]

  def testRecipeHasFields(self):
    """Tests that all recipes have the correct fields."""
    for recipe in self.recipes:
      self.assertIn('name', recipe.contents)
      self.assertIn('short_description', recipe.contents)
      self.assertIn('modules', recipe.contents)
      self.assertIsInstance(recipe.contents['modules'], list)

      self.assertIsInstance(recipe.args, list)

  def testRecipeModulesHaveFields(self):
    """Tests that modules defined in the recipe have the correct fields."""
    for recipe in self.recipes:
      declared_modules = set()
      wanted_modules = set()
      for module in recipe.contents['modules']:
        error_msg = 'module {0:s} in recipe {1:s}'.format(
            module['name'], recipe.contents['name'])

        self.assertIn('wants', module, msg=error_msg)
        self.assertIn('name', module, msg=error_msg)
        self.assertIn('args', module, msg=error_msg)

        declared_modules.add(module['name'])
        for wanted in module['wants']:
          wanted_modules.add(wanted)

        self.assertIsInstance(module['wants'], list, msg=error_msg)
        self.assertIsInstance(module['args'], dict, msg=error_msg)
        self.assertIsInstance(module['name'], six.string_types, msg=error_msg)

      for wanted_module in wanted_modules:
        self.assertIn(wanted_module, declared_modules,
                      msg='recipe: {0:s}'.format(recipe.contents['name']))

if __name__ == '__main__':
  unittest.main()
