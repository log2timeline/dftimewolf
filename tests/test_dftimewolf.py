# -*- coding: utf-8 -*-
"""Tests for DFTimewolf functions."""

from __future__ import unicode_literals

import argparse
from unittest import TestCase

from dftimewolf.lib import utils as dftw_utils
from dftimewolf import config

parser = argparse.ArgumentParser()
parser.add_argument('parameterone')
parser.add_argument('--optional_param')
parser.add_argument('--spaces_param')
parser.add_argument('explosion')


class DFTimewolfTest(TestCase):
  """Tests for dftimewolf_recipes functions."""

  def setUp(self):
    config.Config.clear_extra()

  def test_import_args_from_cli(self):
    """Tries parsing the CLI arguments and updating a recipe dictionary."""

    recipe_args = {
        'recipe_arg1': 'This should remain intact',
        'recipe_arg2': 'This should be replaced: @parameterone',
        'recipe_arg3': 'This should be replaced by @optional_param',
        'recipe_arg4': 'This includes spaces: @spaces_param',
        'recipe_arg5': 'Characters after param: @explosion!',
    }

    expected_args = {
        'recipe_arg1': 'This should remain intact',
        'recipe_arg2': 'This should be replaced: value_for_param_one',
        'recipe_arg3': 'This should be replaced by 3',
        'recipe_arg4': 'This includes spaces: S P A C E',
        'recipe_arg5': 'Characters after param: BOOM!',
    }

    args = parser.parse_args([
        'value_for_param_one',
        '--optional_param', '3',
        '--spaces_param', 'S P A C E',
        'BOOM',
    ])

    imported_args = dftw_utils.import_args_from_dict(
        recipe_args, vars(args), config.Config)

    self.assertEqual(imported_args, expected_args)

  def test_nonexistent_arg(self):
    """Makes sure that an exception is raised for unknown @ variables.

    A recipe writer needs to define a parsing tuple for each @ variable used by
    the recipe.
    """

    recipe_args = {
        'recipe_arg1': 'This should be replaced: @parameterone',
        'recipe_arg2': 'This arg cannot be replaced @nonexistent',
    }

    args = parser.parse_args([
        'value_for_param_one',
        '--optional_param', '3',
        '--spaces_param', 'So unique!',
        'BOOM',
    ])

    with self.assertRaises(ValueError):
      imported = dftw_utils.import_args_from_dict(
          recipe_args, vars(args), config.Config)
      dftw_utils.check_placeholders(imported)

  def test_cli_precedence_over_config(self):
    """Tests that the same argument provided via the CLI overrides the one
    specified in the config file."""

    provided_args = {
        'arg1': 'I want whatever CLI says: @parameterone',
    }
    expected_args = {
        'arg1': 'I want whatever CLI says: CLI WINS!',
    }

    config.Config.load_extra_data('{"parameterone": "CONFIG WINS!"}')
    args = parser.parse_args(['CLI WINS!', 'BOOM'])
    imported_args = dftw_utils.import_args_from_dict(
        provided_args, vars(args), config.Config)
    self.assertEqual(imported_args, expected_args)

  def test_config_fills_missing_args(self):
    """Tests that a configuration file will fill-in arguments that are missing
    from the CLI."""
    provided_args = {'arg1': 'This should remain intact', 'arg2': '@config'}
    expected_args = {
        'arg1': 'This should remain intact',
        'arg2': 'A config arg',
    }
    config.Config.load_extra_data('{"config": "A config arg"}')
    imported_args = dftw_utils.import_args_from_dict(
        provided_args, {}, config.Config)
    self.assertEqual(imported_args, expected_args)
