# -*- coding: utf-8 -*-
"""Tests for DFTimewolf functions."""

import argparse
import unittest

import six

from dftimewolf.lib import utils as dftw_utils
from dftimewolf import config

parser = argparse.ArgumentParser()
parser.add_argument('parameterone')
parser.add_argument('--optional_param')
parser.add_argument('--spaces_param')
parser.add_argument('explosion')


class DFTimewolfTest(unittest.TestCase):
  """Tests for dftimewolf_recipes functions."""

  def _CheckPlaceholders(self, value):
    """Checks if any values in a given dictionary still contain @ parameters.

    Args:
      value (object): Dictionary, list, or string that will be recursively
          checked for placeholders

    Returns:
      object: for a top-level caller, a modified dict with replaced tokens
          or for a recursive caller, a modified object with replaced tokens.

    Raises:
      ValueError: There still exists a value with an @ parameter.
    """
    if isinstance(value, six.string_types):
      if dftw_utils.TOKEN_REGEX.search(value):
        raise ValueError('{0:s} must be replaced in dictionary'.format(value))
    elif isinstance(value, list):
      return [self._CheckPlaceholders(item) for item in value]
    elif isinstance(value, dict):
      return {key: self._CheckPlaceholders(val) for key, val in value.items()}
    elif isinstance(value, tuple):
      return tuple(self._CheckPlaceholders(val) for val in value)
    return value

  def setUp(self):
    config.Config.ClearExtra()

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

    parser.set_defaults(**config.Config.GetExtra())
    args = parser.parse_args([
        'value_for_param_one',
        '--optional_param',
        '3',
        '--spaces_param',
        'S P A C E',
        'BOOM',
    ])

    imported_args = dftw_utils.ImportArgsFromDict(
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
    parser.set_defaults(**config.Config.GetExtra())
    args = parser.parse_args([
        'value_for_param_one',
        '--optional_param',
        '3',
        '--spaces_param',
        'So unique!',
        'BOOM',
    ])

    with self.assertRaises(ValueError):
      imported = dftw_utils.ImportArgsFromDict(
          recipe_args, vars(args), config.Config)
      self._CheckPlaceholders(imported)

  def test_cli_precedence_over_config(self):
    """Tests that the same argument provided via the CLI overrides the one
    specified in the config file."""

    provided_args = {
        'arg1': 'I want whatever CLI says: @parameterone',
    }
    expected_args = {
        'arg1': 'I want whatever CLI says: CLI WINS!',
    }

    config.Config.LoadExtraData('{"parameterone": "CONFIG WINS!"}')
    parser.set_defaults(**config.Config.GetExtra())
    args = parser.parse_args(['CLI WINS!', 'BOOM'])
    imported_args = dftw_utils.ImportArgsFromDict(
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
    config.Config.LoadExtraData('{"config": "A config arg"}')
    parser.set_defaults(**config.Config.GetExtra())
    args = parser.parse_args(['a', 'b'])
    imported_args = dftw_utils.ImportArgsFromDict(
        provided_args, vars(args), config.Config)
    self.assertEqual(imported_args, expected_args)
