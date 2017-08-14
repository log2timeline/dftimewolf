"""Tests for DFTimewolf functions."""
import argparse
from unittest import TestCase
import os
import shutil

from dftimewolf.cli import dftimewolf_recipes

parser = argparse.ArgumentParser()
parser.add_argument('parameterone')
parser.add_argument('--optional_param')
parser.add_argument('--spaces_param')
parser.add_argument('explosion')


class DFTimewolfTest(TestCase):
  """Tests for timeflow_recipes functions."""

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

    imported_args = dftimewolf_recipes.import_args_from_cli(recipe_args, args)
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

    with self.assertRaises(AttributeError):
      dftimewolf_recipes.import_args_from_cli(recipe_args, args)
